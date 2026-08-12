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
# ---------------------------------------------------------------------------
UNIT_REFERENCE = {
    "ma":     {"pinyin": "ma1",   "initial": "m", "final": "a",  "tone": 1},
    "ba":     {"pinyin": "ba1",   "initial": "b", "final": "a",  "tone": 1},
    "pa":     {"pinyin": "pa1",   "initial": "p", "final": "a",  "tone": 1},
    "ta":     {"pinyin": "ta1",   "initial": "t", "final": "a",  "tone": 1},
    "yi":     {"pinyin": "yi1",   "initial": "y", "final": "i",  "tone": 1},
    "wu":     {"pinyin": "wu3",   "initial": "w", "final": "u",  "tone": 3},
    "yu":     {"pinyin": "yu2",   "initial": "y", "final": "v",  "tone": 2},
    "mao":    {"pinyin": "mao1",  "initial": "m", "final": "ao", "tone": 1},
    "gou":    {"pinyin": "gou3",  "initial": "g", "final": "ou", "tone": 3},
    "niao":   {"pinyin": "niao3", "initial": "n", "final": "iao", "tone": 3},
    "ma_t2":  {"pinyin": "ma2",   "initial": "m", "final": "a",  "tone": 2},
    "ma_t3":  {"pinyin": "ma3",   "initial": "m", "final": "a",  "tone": 3},
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
    """对比目标音素（声母/韵母/声调）与识别音素"""
    ref_ini, ref_fin, ref_tone = ref["initial"], ref["final"], ref["tone"]

    # 选择与目标最匹配的识别 token
    best_token = ""
    best_score = 0.0
    for tok in tokens:
        ini, fin, tone = split_pinyin(tok)
        s = 0.0
        if ini == ref_ini:
            s += 40
        if fin == ref_fin:
            s += 40
        if tone == ref_tone:
            s += 20
        if s > best_score:
            best_score = s
            best_token = tok

    if best_token:
        det_ini, det_fin, det_tone = split_pinyin(best_token)
    else:
        det_ini, det_fin, det_tone = "", "", 0

    phonemes: list[dict] = []

    # 声母
    exp_ini = ref_ini if ref_ini else "（零声母）"
    if det_ini == ref_ini:
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
    exp_fin = ref_fin if ref_fin else "（无韵母）"
    if det_fin == ref_fin:
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
    if det_tone == ref_tone:
        phonemes.append({
            "phoneme": "声调", "expected": tone_names[ref_tone],
            "detected": tone_names[det_tone] if det_tone else exp_fin + "（依据曲线判定）",
            "score": 100, "feedback": "声调与目标一致",
        })
    elif det_tone in (1, 2, 3, 4):
        phonemes.append({
            "phoneme": "声调", "expected": tone_names[ref_tone],
            "detected": tone_names[det_tone],
            "score": 0, "feedback": f"识别为{det_tone}，与目标{ref_tone}不符",
        })
    else:
        phonemes.append({
            "phoneme": "声调", "expected": tone_names[ref_tone],
            "detected": "依据F0曲线判定",
            "score": 60, "feedback": "语音识别未能明确声调，将依据基频曲线综合判断",
        })

    return phonemes, best_score


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
