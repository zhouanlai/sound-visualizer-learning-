"""
看得见的声音 - 深度学习音频分析模块

基于 Wav2Vec2 预训练模型（XLSR-53 中文）对用户发音进行深度学习分析：
- 语音识别：将用户音频转换为拼音文本（音素级别分析）
- 声调识别：从识别结果及 F0 曲线中提取并评估声调
- 发音准确度：音素（声母/韵母/声调）与目标发音对比评分
- 流利度评估：基于语音活动检测（VAD）的停顿与语速分析

同时提供 librosa 传统声学特征提取的增强实现：
- 共振峰 F1/F2 使用 LPC 线性预测编码真实估计（替代原有随机值）

推理加速：自动选择 MPS (Apple Silicon) / CUDA / CPU。
模型首次使用自动从 HuggingFace 下载，缓存于 ~/.cache/huggingface。
可通过环境变量 ASR_MODEL_ID 更换模型。
"""
import os

# 关键：必须在 import torch 之前设置。
# Wav2Vec2 使用了 weight_norm，该算子暂未在 MPS(Apple Silicon) 上实现，
# 开启 fallback 让不支持的算子自动回退到 CPU，其余算子仍走 MPS 加速。
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from typing import Optional
import numpy as np
import librosa

# ---------------------------------------------------------------------------
# 深度学习模型（懒加载，首次调用时才加载）
# ---------------------------------------------------------------------------
ASR_MODEL_ID = os.environ.get(
    "ASR_MODEL_ID", "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn"
)

_ASR_LOADED = False
_ASR_ERROR: Optional[str] = None
_processor = None
_model = None
_device = "cpu"


def load_asr_model(force: bool = False) -> bool:
    """懒加载 Wav2Vec2 语音识别模型

    说明：Wav2Vec2 使用了 weight_norm，该算子在 MPS(Apple Silicon) 上暂无原生
    实现（会触发 fallback 但仍可能报错）。为保证稳定推理，ASR 模型统一在 CPU 上
    运行——对于 1~3 秒的发音片段，CPU 推理约 1~3 秒即可完成，速度可接受。
    声学特征（librosa）与共振峰提取走 numpy，与设备无关。
    若有 NVIDIA GPU，可手动将 ASR_DEVICE 改为 "cuda" 以获得加速。
    """
    global _ASR_LOADED, _ASR_ERROR, _processor, _model, _device
    if _ASR_LOADED and not force:
        return True
    try:
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        # ASR 推理设备：CPU 最稳定（weight_norm 原生支持）；GPU 可加速
        _device = os.environ.get("ASR_DEVICE", "cpu")

        _processor = Wav2Vec2Processor.from_pretrained(ASR_MODEL_ID)
        _model = Wav2Vec2ForCTC.from_pretrained(ASR_MODEL_ID)
        _model.to(_device)
        _model.eval()
        _ASR_LOADED = True
        _ASR_ERROR = None
        print(f"[audio_analyzer] ASR 模型加载成功 (model={ASR_MODEL_ID}, device={_device})")
        return True
    except Exception as e:  # noqa: BLE001
        _ASR_LOADED = False
        _ASR_ERROR = str(e)
        print(f"[audio_analyzer] ASR 模型加载失败，降级为传统特征分析: {e}")
        return False


def recognize_speech(audio: np.ndarray, sr: int) -> str:
    """使用 Wav2Vec2 识别语音，返回拼音文本（带声调数字，如 'ma1'）"""
    if not load_asr_model() or _model is None or _processor is None:
        return ""
    import torch

    # 重采样到 16kHz（Wav2Vec2 要求）
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

    try:
        with torch.no_grad():
            # 注意：Wav2Vec2 CTC 推理不需要 attention_mask，
            # 使用 return_attention_mask=True 会导致部分 transformers 版本
            # 返回 input_values 为 None，故仅取 input_values。
            inputs = _processor(
                audio,
                sampling_rate=16000,
                return_tensors="pt",
            )
            input_values = inputs["input_values"].to(_device)
            logits = _model(input_values).logits
            pred_ids = torch.argmax(logits, dim=-1)
        text = _processor.batch_decode(pred_ids)[0]
        return (text or "").strip()
    except Exception as e:  # noqa: BLE001
        print(f"[audio_analyzer] 语音识别失败: {e}")
        return ""


# ---------------------------------------------------------------------------
# 拼音处理工具
# ---------------------------------------------------------------------------
INITIALS = [
    "zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l",
    "g", "k", "h", "j", "q", "x", "r", "z", "c", "s", "y", "w",
]


def split_pinyin(py: str) -> tuple[str, str, int]:
    """拆分拼音为 (声母, 韵母, 声调)。例：'ma3' -> ('m', 'a', 3)"""
    py = py.strip().lower()
    if not py:
        return "", "", 0
    tone = 0
    body = py
    for ch in "1234":
        if ch in body:
            tone = int(ch)
            body = body.replace(ch, "")
            break
    initial = ""
    final = body
    for ini in INITIALS:
        if body.startswith(ini):
            initial = ini
            final = body[len(ini):]
            break
    return initial, final, tone


def extract_pinyin_tokens(text: str) -> list[str]:
    """从识别文本中提取拼音 token 列表"""
    tokens = []
    for word in text.split():
        for tok in word.split("|"):
            tok = tok.strip()
            if tok:
                tokens.append(tok)
    return tokens


# ---------------------------------------------------------------------------
# 标准发音参考库（目标单元）
# 已开放 50 个核心单元（12 个对比单元 + 38 个常用音节）：verified=True 开放检测；其余音节单元仅学习不开放检测
# targets: 该单元检测任务需要朗读的目标音节（对比单元含多个）
# ---------------------------------------------------------------------------
UNIT_REFERENCE = {
    # ===== 附录A 核心单元（检测已验证，可开放） =====
    "a":        {"pinyin": "a1",    "initial": "", "final": "a",  "tone": 1, "verified": True,  "targets": ["a1"]},
    "i":        {"pinyin": "i1",    "initial": "", "final": "i",  "tone": 1, "verified": True,  "targets": ["i1"]},
    "u_u":      {"pinyin": "wu/yu", "initial": "w", "final": "u", "tone": 1, "verified": True,  "targets": ["wu1", "yu1"]},
    "m":        {"pinyin": "ma1",   "initial": "m", "final": "a",  "tone": 1, "verified": True,  "targets": ["ma1"]},
    "b_p":      {"pinyin": "ba/pa", "initial": "b", "final": "a",  "tone": 1, "verified": True,  "targets": ["ba1", "pa1"]},
    "d_t":      {"pinyin": "da/ta", "initial": "d", "final": "a",  "tone": 1, "verified": True,  "targets": ["da1", "ta1"]},
    "n_l":      {"pinyin": "na/la", "initial": "n", "final": "a",  "tone": 1, "verified": True,  "targets": ["na1", "la1"]},
    "g_k":      {"pinyin": "ga/ka", "initial": "g", "final": "a",  "tone": 1, "verified": True,  "targets": ["ga1", "ka1"]},
    "j_q_x":    {"pinyin": "ji/qi/xi", "initial": "j", "final": "i", "tone": 1, "verified": True, "targets": ["ji1", "qi1", "xi1"]},
    "z_zh":     {"pinyin": "za/zha", "initial": "z", "final": "a", "tone": 1, "verified": True, "targets": ["za1", "zha1"]},
    "ma_tone":  {"pinyin": "ma1/2/3/4", "initial": "m", "final": "a", "tone": 1, "verified": True, "targets": ["ma1", "ma2", "ma3", "ma4"]},
    "ma":       {"pinyin": "ma1",   "initial": "m", "final": "a",  "tone": 1, "verified": True,  "targets": ["ma1"]},
    # ===== 已开放单音节单元（共 50 个：12 核心对比 + 38 常用音节，均开放检测） =====
    "ba":       {"pinyin": "ba1",   "initial": "b", "final": "a",  "tone": 1, "verified": True,  "targets": ["ba1"]},
    "pa":       {"pinyin": "pa1",   "initial": "p", "final": "a",  "tone": 1, "verified": True,  "targets": ["pa1"]},
    "ta":       {"pinyin": "ta1",   "initial": "t", "final": "a",  "tone": 1, "verified": True,  "targets": ["ta1"]},
    "yi":       {"pinyin": "yi1",   "initial": "y", "final": "i",  "tone": 1, "verified": True,  "targets": ["yi1"]},
    "wu":       {"pinyin": "wu3",   "initial": "w", "final": "u",  "tone": 3, "verified": True,  "targets": ["wu3"]},
    "yu":       {"pinyin": "yu2",   "initial": "y", "final": "v",  "tone": 2, "verified": True,  "targets": ["yu2"]},
    "mao":      {"pinyin": "mao1",  "initial": "m", "final": "ao", "tone": 1, "verified": True,  "targets": ["mao1"]},
    "gou":      {"pinyin": "gou3",  "initial": "g", "final": "ou", "tone": 3, "verified": True,  "targets": ["gou3"]},
    "niao":     {"pinyin": "niao3", "initial": "n", "final": "iao", "tone": 3, "verified": True,  "targets": ["niao3"]},
    "ma_t2":    {"pinyin": "ma2",   "initial": "m", "final": "a",  "tone": 2, "verified": True,  "targets": ["ma2"]},
    "ma_t3":    {"pinyin": "ma3",   "initial": "m", "final": "a",  "tone": 3, "verified": True,  "targets": ["ma3"]},
    "bo":       {"pinyin": "bo1",   "initial": "b", "final": "o",  "tone": 1, "verified": True,  "targets": ["bo1"]},
    "bi":       {"pinyin": "bi3",   "initial": "b", "final": "i",  "tone": 3, "verified": True,  "targets": ["bi3"]},
    "bu":       {"pinyin": "bu4",   "initial": "b", "final": "u",  "tone": 4, "verified": True,  "targets": ["bu4"]},
    "po":       {"pinyin": "po1",   "initial": "p", "final": "o",  "tone": 1, "verified": True,  "targets": ["po1"]},
    "pi":       {"pinyin": "pi2",   "initial": "p", "final": "i",  "tone": 2, "verified": True,  "targets": ["pi2"]},
    "pu":       {"pinyin": "pu3",   "initial": "p", "final": "u",  "tone": 3, "verified": True,  "targets": ["pu3"]},
    "mo":       {"pinyin": "mo1",   "initial": "m", "final": "o",  "tone": 1, "verified": True,  "targets": ["mo1"]},
    "mi":       {"pinyin": "mi3",   "initial": "m", "final": "i",  "tone": 3, "verified": True,  "targets": ["mi3"]},
    "mu":       {"pinyin": "mu4",   "initial": "m", "final": "u",  "tone": 4, "verified": True,  "targets": ["mu4"]},
    "fa":       {"pinyin": "fa1",   "initial": "f", "final": "a",  "tone": 1, "verified": True,  "targets": ["fa1"]},
    "fei":      {"pinyin": "fei1",  "initial": "f", "final": "ei", "tone": 1, "verified": True,  "targets": ["fei1"]},
    "da":       {"pinyin": "da4",   "initial": "d", "final": "a",  "tone": 4, "verified": True,  "targets": ["da4"]},
    "duo":      {"pinyin": "duo1",  "initial": "d", "final": "uo", "tone": 1, "verified": True,  "targets": ["duo1"]},
    "di":       {"pinyin": "di4",   "initial": "d", "final": "i",  "tone": 4, "verified": True,  "targets": ["di4"]},
    "du":       {"pinyin": "du2",   "initial": "d", "final": "u",  "tone": 2, "verified": True,  "targets": ["du2"]},
    "te":       {"pinyin": "te4",   "initial": "t", "final": "e",  "tone": 4, "verified": True,  "targets": ["te4"]},
    "ti":       {"pinyin": "ti2",   "initial": "t", "final": "i",  "tone": 2, "verified": True,  "targets": ["ti2"]},
    "tu":       {"pinyin": "tu2",   "initial": "t", "final": "u",  "tone": 2, "verified": True,  "targets": ["tu2"]},
    "na":       {"pinyin": "na4",   "initial": "n", "final": "a",  "tone": 4, "verified": True,  "targets": ["na4"]},
    "ni":       {"pinyin": "ni3",   "initial": "n", "final": "i",  "tone": 3, "verified": True,  "targets": ["ni3"]},
    "nu":       {"pinyin": "nu3",   "initial": "n", "final": "u",  "tone": 3, "verified": True,  "targets": ["nu3"]},
    "la":       {"pinyin": "la1",   "initial": "l", "final": "a",  "tone": 1, "verified": True,  "targets": ["la1"]},
    "li":       {"pinyin": "li3",   "initial": "l", "final": "i",  "tone": 3, "verified": True,  "targets": ["li3"]},
    "lu":       {"pinyin": "lu4",   "initial": "l", "final": "u",  "tone": 4, "verified": True,  "targets": ["lu4"]},
    "ge":       {"pinyin": "ge1",   "initial": "g", "final": "e",  "tone": 1, "verified": True,  "targets": ["ge1"]},
    "gu":       {"pinyin": "gu3",   "initial": "g", "final": "u",  "tone": 3, "verified": True,  "targets": ["gu3"]},
    "ka":       {"pinyin": "ka3",   "initial": "k", "final": "a",  "tone": 3, "verified": True,  "targets": ["ka3"]},
}


def unit_verified(unit_id: str) -> bool:
    """该单元检测任务是否已验证开放（分级开放策略 GROW-08）"""
    ref = UNIT_REFERENCE.get(unit_id)
    return bool(ref and ref.get("verified") and ref.get("targets"))


# ---------------------------------------------------------------------------
# 录音质量检测（需求 RES-01：音量/噪声/截幅/时长/静音 五维）
# ---------------------------------------------------------------------------
def analyze_audio_quality(y: np.ndarray, sr: int) -> dict:
    """五维录音质量检测，返回各项状态与总体结论

    维度：音量(RMS)、噪声(SNR估计)、截幅(峰值)、时长(有效时长)、静音比
    status: pass / warn / fail
    """
    eps = 1e-8
    rms = librosa.feature.rms(y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0]
    rms = rms[rms > eps]
    duration = len(y) / sr

    items: list[dict] = []

    # 1. 音量（平均 RMS → dBFS）
    avg_db = 20 * np.log10(rms.mean() + eps) if len(rms) else -120
    if -30 <= avg_db <= -6:
        vol_status, vol_msg = "pass", f"音量适中（{avg_db:.0f}dBFS）"
    elif -45 <= avg_db < -30 or -6 < avg_db <= -2:
        vol_status, vol_msg = "warn", f"音量偏低（{avg_db:.0f}dBFS），建议靠近麦克风" if avg_db < -30 else f"音量偏高（{avg_db:.0f}dBFS），建议稍离远一些"
    else:
        vol_level = "低" if avg_db < -45 else "高"
        vol_status, vol_msg = "fail", f"音量过{vol_level}（{avg_db:.0f}dBFS），请调整距离后重录"
    items.append({"name": "音量", "key": "volume", "status": vol_status, "message": vol_msg})

    # 2. 噪声（SNR 估计：高能量帧均值 / 低能量帧均值）
    if len(rms) >= 10:
        sorted_rms = np.sort(rms)
        high = sorted_rms[-max(1, len(sorted_rms) // 10):].mean()
        low = sorted_rms[:max(1, len(sorted_rms) // 3)].mean()
        snr_db = 20 * np.log10((high + eps) / (low + eps))
    else:
        snr_db = 0.0
    if snr_db >= 15:
        noise_status, noise_msg = "pass", f"环境噪声低（SNR≈{snr_db:.0f}dB）"
    elif snr_db >= 8:
        noise_status, noise_msg = "warn", f"存在背景噪声（SNR≈{snr_db:.0f}dB），建议在安静环境录制"
    else:
        noise_status, noise_msg = "fail", f"背景噪声过大（SNR≈{snr_db:.0f}dB），请到安静环境重录"
    items.append({"name": "噪声", "key": "noise", "status": noise_status, "message": noise_msg})

    # 3. 截幅（峰值接近满幅的比例）
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    clip_ratio = float(np.mean(np.abs(y) > 0.99)) if len(y) else 0.0
    if clip_ratio < 0.001:
        clip_status, clip_msg = "pass", f"无截幅（峰值{peak:.2f}）"
    elif clip_ratio < 0.01:
        clip_status, clip_msg = "warn", f"接近截幅（峰值{peak:.2f}），音量已到临界"
    else:
        clip_status, clip_msg = "fail", "声音截幅（爆音），请远离麦克风或降低音量后重录"
    items.append({"name": "截幅", "key": "clipping", "status": clip_status, "message": clip_msg})

    # 4. 时长（有效时长 0.8~10s）
    if 0.8 <= duration <= 10:
        dur_status, dur_msg = "pass", f"时长合适（{duration:.1f}秒）"
    elif 0.4 <= duration < 0.8 or 10 < duration <= 15:
        dur_level = "短" if duration < 0.8 else "长"
        dur_status, dur_msg = "warn", f"时长偏{dur_level}（{duration:.1f}秒）"
    else:
        dur_status, dur_msg = "fail", f"时长达不到要求（{duration:.1f}秒），请完整朗读后重录"
    items.append({"name": "时长", "key": "duration", "status": dur_status, "message": dur_msg})

    # 5. 静音比（能量低于阈值的帧占比）
    silence_ratio = float(np.mean(rms < 0.01)) if len(rms) else 1.0
    if silence_ratio < 0.4:
        sil_status, sil_msg = "pass", f"有效发声占比高（静音比{silence_ratio:.0%}）"
    elif silence_ratio < 0.7:
        sil_status, sil_msg = "warn", f"静音偏多（静音比{silence_ratio:.0%}），请连贯朗读"
    else:
        sil_status, sil_msg = "fail", "有效语音过少（多为静音），请对着麦克风清晰朗读后重录"
    items.append({"name": "静音比", "key": "silence", "status": sil_status, "message": sil_msg})

    # 总体结论
    statuses = [i["status"] for i in items]
    if "fail" in statuses:
        passed, score, summary = False, 40, "录音质量不达标，请按提示调整后重录"
    elif "warn" in statuses:
        passed, score, summary = True, 75, "录音可用，但存在可改进项，建议重录以获得更准结果"
    else:
        passed, score, summary = True, 100, "录音质量良好，可以正常分析"
    return {
        "passed": passed,
        "score": score,
        "summary": summary,
        "items": items,
    }


# ---------------------------------------------------------------------------
# 声学特征提取（真实分析，无随机值）
# ---------------------------------------------------------------------------
FRAME_LENGTH = 2048
HOP_LENGTH = 512


def lpc_yule_walker(x: np.ndarray, order: int = 14) -> np.ndarray:
    """Yule-Walker 方程求解 LPC 系数"""
    try:
        from scipy.linalg import toeplitz
    except ImportError:
        return np.zeros(order + 1)
    x = x - np.mean(x)
    n = len(x)
    if n <= order + 1:
        return np.zeros(order + 1)
    r = np.correlate(x, x, "full")[n - 1: n + order]
    try:
        R = toeplitz(r[:-1])
        a = -np.linalg.solve(R, r[1:])
    except (np.linalg.LinAlgError, ValueError):
        return np.zeros(order + 1)
    return np.concatenate(([1.0], a))


def estimate_formants(y: np.ndarray, sr: int) -> tuple[list[float], list[float]]:
    """使用 LPC 线性预测编码真实估计共振峰 F1/F2"""
    frames = librosa.util.frame(y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)
    f1_list: list[float] = []
    f2_list: list[float] = []
    for i in range(frames.shape[1]):
        frame = frames[:, i].copy()
        # 预加重
        frame = np.append(frame[0], frame[1:] - 0.97 * frame[:-1])
        # 加窗
        frame = frame * np.hanning(len(frame))
        # 静音帧跳过
        if np.sqrt(np.mean(frame ** 2)) < 1e-6:
            f1_list.append(0.0)
            f2_list.append(0.0)
            continue
        a = lpc_yule_walker(frame)
        if np.all(a == 0):
            f1_list.append(0.0)
            f2_list.append(0.0)
            continue
        roots = np.roots(a)
        roots = [r for r in roots if np.imag(r) > 0 and 0.5 < np.abs(r) < 1.0]
        if not roots:
            f1_list.append(0.0)
            f2_list.append(0.0)
            continue
        # 计算频率与带宽，按带宽排序选取稳定共振峰
        freqs_bw = []
        for r in roots:
            freq = np.abs(np.angle(r)) * sr / (2 * np.pi)
            if freq < 100 or freq > sr / 2 - 200:
                continue
            bw = -np.log(np.abs(r)) * sr / np.pi
            freqs_bw.append((freq, bw))
        freqs_bw.sort(key=lambda x: x[1])
        formants = [f for f, _ in freqs_bw[:2]]
        while len(formants) < 2:
            formants.append(0.0)
        f1_list.append(float(formants[0]))
        f2_list.append(float(formants[1]))
    return f1_list, f2_list


def compute_fluency_score(y: np.ndarray, sr: int) -> float:
    """基于语音活动检测（VAD）的真实流利度评分"""
    rms = librosa.feature.rms(
        y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH
    )[0]
    if len(rms) == 0 or rms.max() < 1e-8:
        return 0.0
    floor = float(np.percentile(rms, 20))
    peak = float(rms.max())
    threshold = max(floor * 2.0, peak * 0.08)
    voiced = rms >= threshold
    if not np.any(voiced):
        return 10.0
    frame_time = HOP_LENGTH / sr
    total_dur = len(voiced) * frame_time
    voiced_dur = float(np.sum(voiced)) * frame_time
    voice_ratio = voiced_dur / total_dur if total_dur > 0 else 0.0

    # 统计停顿次数与总停顿时长
    pauses = 0
    total_pause = 0.0
    in_pause = False
    for v in voiced:
        if not v:
            if not in_pause:
                pauses += 1
                in_pause = True
            total_pause += frame_time
        else:
            in_pause = False

    score = 100.0
    # 有效发声比例过低的惩罚
    if voice_ratio < 0.3:
        score -= 30
    # 停顿惩罚
    pause_ratio = total_pause / (voiced_dur + 1e-6)
    score -= min(40, pause_ratio * 40)
    return float(max(10.0, min(100.0, score)))


# ---------------------------------------------------------------------------
# 标准声调曲线模板
# ---------------------------------------------------------------------------
def standard_tone_curve(tone: int, n: int = 100) -> np.ndarray:
    """生成标准声调 F0 曲线模板"""
    t = np.linspace(0, 1, n)
    if tone == 1:      # 阴平：高平
        return np.full(n, 200.0)
    if tone == 2:      # 阳平：上升
        return 140 + 60 * t
    if tone == 3:      # 上声：先降后升
        return 185 - 65 * t + 105 * np.maximum(0, t - 0.5)
    if tone == 4:      # 去声：下降
        return 220 - 80 * t
    return np.full(n, 180.0)


def resample_1d(x: np.ndarray, n: int) -> np.ndarray:
    """将数组线性重采样到指定长度"""
    if len(x) < 2:
        return np.full(n, float(x[0]) if len(x) else 0.0)
    idx = np.linspace(0, len(x) - 1, n).astype(int)
    return np.asarray(x, dtype=np.float64)[idx]


def tone_shape_score(f0_voiced: np.ndarray, ref_tone: int) -> float:
    """通过 F0 曲线形状与标准声调模板的相关系数评估声调准确性"""
    if len(f0_voiced) < 5:
        return 0.0
    standard = standard_tone_curve(ref_tone)
    user_curve = resample_1d(f0_voiced, len(standard))
    # 避免常数数组导致相关系数除零（出现 RuntimeWarning / NaN）
    if np.std(user_curve) < 1e-6 or np.std(standard) < 1e-6:
        return 50.0
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.corrcoef(user_curve, standard)[0, 1]
    if np.isnan(corr):
        corr = 0.0
    return float(max(0.0, min(100.0, 55 + corr * 45)))


# ---------------------------------------------------------------------------
# 音素级对比评分
# ---------------------------------------------------------------------------
def compare_phonemes(
    ref: dict, tokens: list[str]
) -> tuple[list[dict], float]:
    """对比目标音素（声母/韵母/声调）与识别音素

    对比单元（targets 多个，如 b_p、ma_tone）按目标逐个匹配最佳识别
    token；单目标单元行为与原有逻辑一致。
    """
    targets = ref.get("targets") or [ref["pinyin"]]
    used: set[int] = set()
    all_phonemes: list[dict] = []
    scores: list[float] = []

    for tgt in targets:
        tgt_ini, tgt_fin, tgt_tone = split_pinyin(tgt)

        # 在未使用的识别 token 中寻找与当前目标最匹配者
        best_idx, best_score = -1, 0.0
        for i, tok in enumerate(tokens):
            if i in used:
                continue
            ini, fin, tone = split_pinyin(tok)
            s = 0.0
            if ini == tgt_ini:
                s += 40
            if fin == tgt_fin:
                s += 40
            if tone == tgt_tone:
                s += 20
            if s > best_score:
                best_score, best_idx = s, i

        if best_idx >= 0:
            used.add(best_idx)
            tok = tokens[best_idx]
        else:
            tok = ""

        if tok:
            det_ini, det_fin, det_tone = split_pinyin(tok)
        else:
            det_ini, det_fin, det_tone = "", "", 0

        phonemes: list[dict] = []

        # 声母
        exp_ini = tgt_ini if tgt_ini else "（零声母）"
        if det_ini == tgt_ini:
            phonemes.append({
                "phoneme": "声母", "expected": exp_ini, "detected": det_ini or exp_ini,
                "score": 100, "feedback": "声母发音准确",
            })
        elif det_ini:
            phonemes.append({
                "phoneme": "声母", "expected": exp_ini, "detected": det_ini,
                "score": 0, "feedback": f"检测到「{det_ini}」，与目标「{exp_ini}」不符",
            })
        else:
            phonemes.append({
                "phoneme": "声母", "expected": exp_ini, "detected": "未检测到",
                "score": 0, "feedback": "未检测到声母发音，请确认是否录入完整",
            })

        # 韵母
        exp_fin = tgt_fin if tgt_fin else "（无韵母）"
        if det_fin == tgt_fin:
            phonemes.append({
                "phoneme": "韵母", "expected": exp_fin, "detected": det_fin or exp_fin,
                "score": 100, "feedback": "韵母发音准确",
            })
        elif det_fin:
            phonemes.append({
                "phoneme": "韵母", "expected": exp_fin, "detected": det_fin,
                "score": 0, "feedback": f"检测到「{det_fin}」，与目标「{exp_fin}」不符",
            })
        else:
            phonemes.append({
                "phoneme": "韵母", "expected": exp_fin, "detected": "未检测到",
                "score": 0, "feedback": "未检测到韵母发音",
            })

        # 声调
        tone_names = {0: "（无法判定）", 1: "第一声", 2: "第二声", 3: "第三声", 4: "第四声"}
        if det_tone == tgt_tone:
            phonemes.append({
                "phoneme": "声调", "expected": tone_names[tgt_tone],
                "detected": tone_names[det_tone] if det_tone else exp_fin + "（依据曲线判定）",
                "score": 100, "feedback": "声调与目标一致",
            })
        elif det_tone in (1, 2, 3, 4):
            phonemes.append({
                "phoneme": "声调", "expected": tone_names[tgt_tone],
                "detected": tone_names[det_tone],
                "score": 0, "feedback": f"识别为{det_tone}，与目标{tgt_tone}不符",
            })
        else:
            phonemes.append({
                "phoneme": "声调", "expected": tone_names[tgt_tone],
                "detected": "依据F0曲线判定",
                "score": 60, "feedback": "语音识别未能明确声调，将依据基频曲线综合判断",
            })

        if len(targets) > 1:
            for p in phonemes:
                p["target"] = tgt
                p["targetChar"] = tgt
        all_phonemes.extend(phonemes)
        scores.append(best_score)

    return all_phonemes, round(sum(scores) / len(scores), 1) if scores else 0.0


# ---------------------------------------------------------------------------
# 深度学习分析总入口
# ---------------------------------------------------------------------------
def analyze_with_deep_learning(
    audio: np.ndarray, sr: int, unit_id: str, f0_voiced: np.ndarray
) -> dict:
    """深度学习分析入口：语音识别 + 音素对比 + 声调评估"""
    result: dict = {
        "recognized_text": "",
        "detected_tone": 0,
        "tone_score": 0.0,
        "phoneme_score": 0.0,
        "phonemes": [],
    }

    ref = UNIT_REFERENCE.get(unit_id)
    if ref is None:
        return result

    targets = ref.get("targets") or [ref["pinyin"]]
    multi = len(targets) > 1

    # 语音识别（音素级别分析）
    text = recognize_speech(audio, sr)
    result["recognized_text"] = text
    tokens = extract_pinyin_tokens(text)

    # 音素对比
    if tokens:
        phonemes, ph_score = compare_phonemes(ref, tokens)
        result["phonemes"] = phonemes
        result["phoneme_score"] = round(ph_score, 1)

    # 声调识别与评估
    detected_tone = 0
    for tok in tokens:
        _, _, t = split_pinyin(tok)
        if t:
            detected_tone = t
            break
    result["detected_tone"] = detected_tone

    if multi:
        # 对比/四声单元：声调分由各目标声调匹配平均体现（曲线分段评估留待专项）
        tone_matches = [p for p in result["phonemes"] if p["phoneme"] == "声调"]
        result["tone_score"] = round(
            sum(p["score"] for p in tone_matches) / len(tone_matches), 1
        ) if tone_matches else 60.0
    else:
        shape = tone_shape_score(f0_voiced, ref["tone"])
        if detected_tone in (1, 2, 3, 4) and detected_tone != ref["tone"]:
            # 识别声调与目标不符，声调分压低
            result["tone_score"] = round(min(shape, 45.0), 1)
        else:
            result["tone_score"] = round(shape, 1)

    return result


def asr_status() -> dict:
    """返回模型加载状态（供调试）"""
    return {
        "loaded": _ASR_LOADED,
        "model": ASR_MODEL_ID,
        "device": _device,
        "error": _ASR_ERROR,
    }
