"""
看得见的声音 - 智能发音学习平台 后端服务
使用FastAPI + Librosa + PyTorch(深度学习)实现音频分析和发音评估
"""
import os
import io
import json
import tempfile
import numpy as np
from typing import Optional

# 必须在 import torch 之前设置：Wav2Vec2 使用 weight_norm，MPS(Apple Silicon)
# 暂未实现该算子，开启 fallback 让不支持的算子回退 CPU，其余仍走 MPS 加速。
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
import librosa
import torch

import database
from audio_analyzer import (
    analyze_with_deep_learning,
    estimate_formants,
    compute_fluency_score,
    asr_status,
    load_asr_model,
    standard_tone_curve,
    UNIT_REFERENCE,
)

app = FastAPI(title="看得见的声音 API", version="1.0.0")

# 启动时初始化 SQLite 数据库（幂等建表）
database.init_db()

# CORS配置 - 允许所有本地开发端口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class PhonemeResult(BaseModel):
    phoneme: str          # 声母 / 韵母 / 声调
    expected: str
    detected: str
    score: float
    feedback: str

class AudioAnalysisResult(BaseModel):
    f0: list[float]
    f1: list[float]
    f2: list[float]
    energy: list[float]
    duration: float
    sample_rate: int
    mfcc: list[list[float]]
    # 深度学习分析结果
    recognized_text: str = ""
    detected_tone: int = 0
    tone_score: float = 0.0
    phoneme_score: float = 0.0
    phonemes: list[PhonemeResult] = []
    # 标准声调曲线（由后端生成，供前端对比展示）
    standard_f0: list[float] = []

class FeedbackItem(BaseModel):
    type: str  # error, warning, suggestion
    category: str  # tone, pronunciation, fluency, rhythm
    message: str
    detail: str
    improvement: str

class PronunciationAssessment(BaseModel):
    score: float
    accuracy: float
    fluency: float
    pronunciation: float
    feedback: list[FeedbackItem]
    audio_analysis: AudioAnalysisResult

# 标准发音参数（模拟）
STANDARD_PARAMS = {
    "ma": {"f0_mean": 200, "f0_std": 10, "f1_range": (200, 400), "f2_range": (800, 1200), "tone": 1},
    "ba": {"f0_mean": 200, "f0_std": 10, "f1_range": (200, 400), "f2_range": (800, 1200), "tone": 1},
    "pa": {"f0_mean": 200, "f0_std": 10, "f1_range": (200, 400), "f2_range": (800, 1200), "tone": 1},
    "ta": {"f0_mean": 200, "f0_std": 10, "f1_range": (200, 400), "f2_range": (800, 1200), "tone": 1},
    "yi": {"f0_mean": 200, "f0_std": 10, "f1_range": (200, 350), "f2_range": (1800, 2400), "tone": 1},
    "wu": {"f0_mean": 180, "f0_std": 15, "f1_range": (250, 400), "f2_range": (600, 900), "tone": 3},
    "yu": {"f0_mean": 220, "f0_std": 15, "f1_range": (200, 350), "f2_range": (1800, 2200), "tone": 2},
    "ma_t2": {"f0_mean": 220, "f0_std": 20, "f1_range": (200, 400), "f2_range": (800, 1200), "tone": 2},
    "ma_t3": {"f0_mean": 180, "f0_std": 25, "f1_range": (200, 400), "f2_range": (800, 1200), "tone": 3},
}

def analyze_audio(audio_data: np.ndarray, sr: int) -> AudioAnalysisResult:
    """分析音频，提取声学特征（共振峰使用LPC真实估计，无随机值）"""
    # 基频F0
    f0, voiced_flag, voiced_probs = librosa.pyin(
        audio_data, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'), sr=sr
    )
    f0 = np.nan_to_num(f0, nan=0.0).tolist()
    
    # MFCC特征
    mfcc = librosa.feature.mfcc(y=audio_data, sr=sr, n_mfcc=13)
    mfcc_list = mfcc.tolist()
    
    # 能量
    energy = librosa.feature.rms(y=audio_data)[0].tolist()
    
    # 共振峰（LPC线性预测真实估计）
    f1, f2 = estimate_formants(audio_data, sr)
    
    duration = len(audio_data) / sr
    
    return AudioAnalysisResult(
        f0=f0,
        f1=f1,
        f2=f2,
        energy=energy,
        duration=duration,
        sample_rate=sr,
        mfcc=mfcc_list
    )

def assess_pronunciation(
    audio_analysis: AudioAnalysisResult, unit_id: str, fluency: float
) -> PronunciationAssessment:
    """评估发音质量（流利度为真实VAD计算，非随机值）"""
    standard = STANDARD_PARAMS.get(unit_id, STANDARD_PARAMS["ma"])
    
    # 计算基频相似度
    f0_array = np.array(audio_analysis.f0)
    f0_voiced = f0_array[f0_array > 0]
    
    if len(f0_voiced) > 0:
        f0_mean = np.mean(f0_voiced)
        f0_std = np.std(f0_voiced)
        f0_similarity = max(0, 100 - abs(f0_mean - standard["f0_mean"]) / standard["f0_mean"] * 100)
        tone_stability = max(0, 100 - f0_std / standard["f0_std"] * 20)
    else:
        f0_mean = 0
        f0_similarity = 0
        tone_stability = 0
    
    # 流利度：由调用方传入（真实VAD计算）
    fluency = fluency if fluency > 0 else 50.0
    
    # 发音准确度 = 音素级深度学习评分 与 基频相似度 加权
    phoneme_score = audio_analysis.phoneme_score  # 0-100，来自Wav2Vec2音素对比
    if phoneme_score > 0:
        accuracy = (phoneme_score * 0.5 + f0_similarity * 0.3 + tone_stability * 0.2)
    else:
        accuracy = (f0_similarity * 0.6 + tone_stability * 0.4)
    
    # 声调评估（深度学习声调评分 + 基频稳定性）
    tone_score = audio_analysis.tone_score  # 0-100，来自F0曲线形状与识别声调
    if tone_score > 0:
        tone_combined = tone_score * 0.6 + tone_stability * 0.4
    else:
        tone_combined = tone_stability
    
    pronunciation = (accuracy * 0.5 + tone_combined * 0.3 + fluency * 0.2)
    score = (accuracy * 0.35 + tone_combined * 0.25 + fluency * 0.2 + pronunciation * 0.2)
    
    # 生成反馈
    feedback = []
    
    if tone_combined < 70:
        feedback.append(FeedbackItem(
            type="error",
            category="tone",
            message="声调偏差较大",
            detail=f"您的平均基频为{f0_mean:.0f}Hz，标准约为{standard['f0_mean']}Hz，声调曲线与标准声调形状相关性偏低",
            improvement="请仔细听示范音频，调整声带张力，注意声调的高低走向"
        ))
    elif tone_combined < 85:
        feedback.append(FeedbackItem(
            type="warning",
            category="tone",
            message="声调基本正确，有提升空间",
            detail="声调曲线与标准有轻微偏差",
            improvement="注意声调的起始和结束位置"
        ))
    else:
        feedback.append(FeedbackItem(
            type="suggestion",
            category="tone",
            message="声调表现优秀",
            detail="声调曲线与标准高度一致",
            improvement="继续保持！"
        ))
    
    if phoneme_score > 0 and phoneme_score < 80:
        # 音素级反馈（来自深度学习识别结果）
        for ph in audio_analysis.phonemes[:2]:
            if ph.score < 100:
                feedback.append(FeedbackItem(
                    type="error" if ph.score < 50 else "warning",
                    category="pronunciation",
                    message=f"{ph.phoneme}发音需改进",
                    detail=ph.feedback,
                    improvement="参考3D发音动画，调整舌位和口型"
                ))
    
    if fluency < 70:
        feedback.append(FeedbackItem(
            type="warning",
            category="fluency",
            message="发音流畅度需要提升",
            detail=f"检测到发音存在停顿或不连贯（流利度{fluency:.0f}分）",
            improvement="多练习，提高发音的连贯性"
        ))
    
    return PronunciationAssessment(
        score=round(score, 1),
        accuracy=round(accuracy, 1),
        fluency=round(fluency, 1),
        pronunciation=round(pronunciation, 1),
        feedback=feedback,
        audio_analysis=audio_analysis
    )

@app.get("/")
async def root():
    return {"message": "看得见的声音 API", "version": "1.0.0"}

@app.get("/api/pronunciation-units")
async def get_pronunciation_units():
    """获取所有发音单元"""
    units = [
        {"id": "ma", "pinyin": "mā", "character": "妈", "category": "声母", "order": 1},
        {"id": "ba", "pinyin": "bā", "character": "八", "category": "声母", "order": 2},
        {"id": "pa", "pinyin": "pā", "character": "趴", "category": "声母", "order": 3},
        {"id": "ta", "pinyin": "tā", "character": "他", "category": "声母", "order": 4},
        {"id": "yi", "pinyin": "yī", "character": "一", "category": "韵母", "order": 5},
        {"id": "wu", "pinyin": "wǔ", "character": "五", "category": "韵母", "order": 6},
        {"id": "yu", "pinyin": "yú", "character": "鱼", "category": "韵母", "order": 7},
        {"id": "mao", "pinyin": "māo", "character": "猫", "category": "声母", "order": 8},
        {"id": "gou", "pinyin": "gǒu", "character": "狗", "category": "声母", "order": 9},
        {"id": "niao", "pinyin": "niǎo", "character": "鸟", "category": "声母", "order": 10},
        {"id": "ma_t2", "pinyin": "má", "character": "麻", "category": "声调", "order": 11},
        {"id": "ma_t3", "pinyin": "mǎ", "character": "马", "category": "声调", "order": 12},
    ]
    return {"code": 200, "data": units}

@app.post("/api/audio/analyze")
async def analyze_audio_file(
    audio: UploadFile = File(...),
    unit_id: str = Form(...)
):
    """分析上传的音频文件"""
    try:
        # 读取音频数据
        audio_bytes = await audio.read()
        
        # 根据content_type确定文件扩展名
        content_type = audio.content_type or ""
        if "webm" in content_type:
            suffix = ".webm"
        elif "ogg" in content_type:
            suffix = ".ogg"
        elif "mp3" in content_type:
            suffix = ".mp3"
        else:
            suffix = ".wav"
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        # 如果是webm/ogg格式，先用ffmpeg转换为wav
        wav_path = tmp_path
        if suffix in [".webm", ".ogg", ".mp3"]:
            wav_path = tmp_path + ".wav"
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-i", tmp_path, "-ar", "16000", "-ac", "1", "-y", wav_path],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"FFmpeg转换失败: {result.stderr}")
                # 如果转换失败，尝试直接加载
                wav_path = tmp_path
        
        # 使用librosa加载音频
        y, sr = librosa.load(wav_path, sr=None)
        
        # 删除临时文件
        os.unlink(tmp_path)
        if wav_path != tmp_path and os.path.exists(wav_path):
            os.unlink(wav_path)
        
        # 分析音频（声学特征：F0/MFCC/能量/共振峰）
        analysis = analyze_audio(y, sr)
        
        # 深度学习分析（Wav2Vec2语音识别 + 音素对比 + 声调评估）
        f0_array = np.array(analysis.f0)
        f0_voiced = f0_array[f0_array > 0]
        deep = analyze_with_deep_learning(y, sr, unit_id, f0_voiced)
        analysis.recognized_text = deep["recognized_text"]
        analysis.detected_tone = deep["detected_tone"]
        analysis.tone_score = deep["tone_score"]
        analysis.phoneme_score = deep["phoneme_score"]
        analysis.phonemes = deep["phonemes"]
        
        # 真实流利度（VAD停顿/语速分析）
        fluency = compute_fluency_score(y, sr)
        
        # 标准声调曲线（由后端基于目标单元声调生成，供前端对比展示）
        ref = UNIT_REFERENCE.get(unit_id)
        if ref:
            n_frames = len(analysis.f0) or 100
            analysis.standard_f0 = standard_tone_curve(ref["tone"], n_frames).tolist()
        
        # 评估发音
        assessment = assess_pronunciation(analysis, unit_id, fluency)
        
        return {
            "code": 200,
            "message": "分析完成",
            "data": assessment.model_dump()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"分析失败: {str(e)}"}
        )

@app.get("/api/asr/status")
async def get_asr_status():
    """获取深度学习模型加载状态（调试用）"""
    return {"code": 200, "data": asr_status()}

@app.post("/api/asr/load")
async def load_asr_endpoint():
    """手动触发深度学习模型加载（可选，用于预热）"""
    ok = load_asr_model()
    return {"code": 200, "data": {"loaded": ok, **asr_status()}}

class UserProgress(BaseModel):
    userId: str
    totalUnits: int = 12
    completedUnits: int = 0
    totalPractice: int = 0
    averageScore: float = 0.0
    lastPracticeAt: str = ""
    unitProgress: list[dict] = []

@app.get("/api/users/{user_id}/progress")
async def get_user_progress(user_id: str):
    """获取用户进度（读 SQLite，用户不存在时自动初始化）"""
    progress = database.get_user_progress(user_id)
    return {"code": 200, "data": progress}

@app.post("/api/users/{user_id}/progress")
async def update_user_progress(user_id: str, progress: UserProgress):
    """更新用户进度（写入 SQLite，兼容旧调用方）"""
    database.update_user_progress(user_id, progress.model_dump())
    return {"code": 200, "message": "进度已更新"}

@app.get("/api/users/{user_id}/learning-records")
async def get_learning_records(user_id: str, limit: int = 20):
    """获取用户学习记录（不含音频 BLOB，音频走 /audio 接口）"""
    records = database.get_learning_records(user_id, limit)
    return {"code": 200, "data": records}

@app.post("/api/learning-records")
async def create_learning_record(
    userId: str = Form(...),
    unitId: str = Form(...),
    pinyin: str = Form(...),
    character: str = Form(...),
    score: float = Form(...),
    accuracy: float = Form(...),
    fluency: float = Form(...),
    pronunciation: float = Form(...),
    duration: float = Form(0.0),
    feedback: str = Form(""),
    audio: UploadFile = File(...),
):
    """创建学习记录：录音二进制(multipart) + 评估结果一并落库，同一事务更新进度"""
    audio_bytes = await audio.read()
    audio_type = audio.content_type or "audio/webm"
    record_id = database.create_learning_record(
        user_id=userId,
        unit_id=unitId,
        pinyin=pinyin,
        character=character,
        score=score,
        accuracy=accuracy,
        fluency=fluency,
        pronunciation=pronunciation,
        duration=duration,
        feedback=feedback,
        audio_blob=audio_bytes,
        audio_type=audio_type,
    )
    print(f"[database] 学习记录已保存 record_id={record_id} user={userId} unit={unitId} score={score}")
    return {"code": 200, "message": "记录已保存", "data": {"id": record_id}}

@app.get("/api/learning-records/{record_id}/audio")
async def get_record_audio(record_id: str):
    """按需返回录音二进制流（后台管理 / 历史记录重听共用）"""
    result = database.get_audio(record_id)
    if result is None:
        return JSONResponse(status_code=404, content={"code": 404, "message": "录音不存在"})
    blob, mime = result
    return Response(content=blob, media_type=mime)

@app.get("/api/admin/learning-records")
async def admin_learning_records(limit: int = 100):
    """后台管理：获取全部用户的学习记录（不含 BLOB）"""
    records = database.get_all_learning_records(limit)
    return {"code": 200, "data": records}

@app.get("/api/admin/stats")
async def admin_stats():
    """后台管理：全量统计卡片数据（SQL 聚合）"""
    stats = database.get_stats()
    return {"code": 200, "data": stats}

@app.websocket("/ws/audio-stream")
async def audio_stream_websocket(websocket: WebSocket):
    """WebSocket实时音频流分析"""
    await websocket.accept()
    
    try:
        while True:
            # 接收音频数据
            data = await websocket.receive_bytes()
            
            # 将字节数据转换为numpy数组
            audio_array = np.frombuffer(data, dtype=np.float32)
            
            # 实时分析（简化版）
            if len(audio_array) > 0:
                # 计算能量
                energy = float(np.sqrt(np.mean(audio_array ** 2)))
                
                # 发送实时数据
                await websocket.send_json({
                    "type": "realtime_data",
                    "energy": energy,
                    "samples": len(audio_array)
                })
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)