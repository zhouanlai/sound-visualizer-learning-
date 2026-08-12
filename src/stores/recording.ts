import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RecordingState, AudioAnalysisResult, PronunciationAssessment } from '@/types'

export const useRecordingStore = defineStore('recording', () => {
  // 状态
  const recordingState = ref<RecordingState>({
    isRecording: false,
    isPaused: false,
    duration: 0,
    audioBlob: null,
    audioUrl: null,
  })

  const analysisResult = ref<AudioAnalysisResult | null>(null)
  const assessment = ref<PronunciationAssessment | null>(null)
  const isAnalyzing = ref(false)
  const error = ref<string | null>(null)

  // 录音相关
  let mediaRecorder: MediaRecorder | null = null
  let audioChunks: Blob[] = []
  let timerInterval: number | null = null
  let audioContext: AudioContext | null = null
  let analyser: AnalyserNode | null = null
  let microphone: MediaStreamAudioSourceNode | null = null

  // 计算属性
  const isRecording = computed(() => recordingState.value.isRecording)
  const isPaused = computed(() => recordingState.value.isPaused)
  const duration = computed(() => recordingState.value.duration)
  const audioUrl = computed(() => recordingState.value.audioUrl)
  const hasRecording = computed(() => recordingState.value.audioBlob !== null)

  const formattedDuration = computed(() => {
    const minutes = Math.floor(recordingState.value.duration / 60)
    const seconds = recordingState.value.duration % 60
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  })

  // 动作
  async function startRecording() {
    try {
      error.value = null
      
      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // 创建MediaRecorder
      mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      })
      
      audioChunks = []
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data)
        }
      }
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
        recordingState.value.audioBlob = audioBlob
        recordingState.value.audioUrl = URL.createObjectURL(audioBlob)
        
        // 停止所有音轨
        stream.getTracks().forEach(track => track.stop())
      }
      
      // 设置音频分析
      audioContext = new AudioContext()
      analyser = audioContext.createAnalyser()
      analyser.fftSize = 2048
      
      microphone = audioContext.createMediaStreamSource(stream)
      microphone.connect(analyser)
      
      // 开始录音
      mediaRecorder.start(100) // 每100ms收集一次数据
      recordingState.value.isRecording = true
      recordingState.value.isPaused = false
      recordingState.value.duration = 0
      
      // 开始计时
      timerInterval = window.setInterval(() => {
        recordingState.value.duration++
      }, 1000)
      
    } catch (err) {
      error.value = '无法访问麦克风，请检查权限设置'
      console.error('录音启动失败:', err)
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
    
    if (timerInterval) {
      clearInterval(timerInterval)
      timerInterval = null
    }
    
    if (audioContext) {
      audioContext.close()
      audioContext = null
    }
    
    recordingState.value.isRecording = false
    recordingState.value.isPaused = false
  }

  function pauseRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.pause()
      recordingState.value.isPaused = true
      
      if (timerInterval) {
        clearInterval(timerInterval)
        timerInterval = null
      }
    }
  }

  function resumeRecording() {
    if (mediaRecorder && mediaRecorder.state === 'paused') {
      mediaRecorder.resume()
      recordingState.value.isPaused = false
      
      // 恢复计时
      timerInterval = window.setInterval(() => {
        recordingState.value.duration++
      }, 1000)
    }
  }

  function clearRecording() {
    if (recordingState.value.audioUrl) {
      URL.revokeObjectURL(recordingState.value.audioUrl)
    }
    
    recordingState.value = {
      isRecording: false,
      isPaused: false,
      duration: 0,
      audioBlob: null,
      audioUrl: null,
    }
    
    analysisResult.value = null
    assessment.value = null
    error.value = null
  }

  // 将后端返回的 snake_case 字段映射为前端 camelCase 类型
  function mapAudioAnalysis(raw: any): AudioAnalysisResult {
    return {
      f0: raw.f0 || [],
      f1: raw.f1 || [],
      f2: raw.f2 || [],
      energy: raw.energy || [],
      duration: raw.duration || 0,
      sampleRate: raw.sample_rate || 0,
      mfcc: raw.mfcc || [],
      recognizedText: raw.recognized_text || '',
      detectedTone: raw.detected_tone || 0,
      toneScore: raw.tone_score || 0,
      phonemeScore: raw.phoneme_score || 0,
      phonemes: (raw.phonemes || []).map((p: any) => ({
        phoneme: p.phoneme,
        expected: p.expected,
        detected: p.detected,
        score: p.score,
        feedback: p.feedback,
      })),
      standardF0: raw.standard_f0 || [],
    }
  }

  async function analyzeRecording(unitId: string) {
    if (!recordingState.value.audioBlob) {
      error.value = '没有录音可分析'
      return
    }

    isAnalyzing.value = true
    error.value = null
    // 清空上一次的分析结果，避免展示过期数据
    analysisResult.value = null
    assessment.value = null

    try {
      // 调用后端API进行真实音频分析（后端完成所有分析后返回结果）
      const formData = new FormData()
      formData.append('audio', recordingState.value.audioBlob, 'recording.webm')
      formData.append('unit_id', unitId)

      const response = await fetch('http://localhost:8000/api/audio/analyze', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`服务器错误: ${response.status}`)
      }

      const result = await response.json()

      if (result.code === 200 && result.data) {
        const data = result.data
        const mapped = mapAudioAnalysis(data.audio_analysis)
        analysisResult.value = mapped
        assessment.value = {
          score: data.score,
          accuracy: data.accuracy,
          fluency: data.fluency,
          pronunciation: data.pronunciation,
          feedback: data.feedback,
          audioAnalysis: mapped,
        }
      } else {
        throw new Error(result.message || '分析失败')
      }
    } catch (err: any) {
      // 后端不可用时不再生成假数据，直接报错提示
      console.error('后端分析失败:', err.message)
      error.value = `分析失败：${err.message || '后端服务不可用'}。请确认后端服务已启动（python backend/main.py）。`
      analysisResult.value = null
      assessment.value = null
    } finally {
      isAnalyzing.value = false
    }
  }

  function getAnalyser() {
    return analyser
  }

  function clearError() {
    error.value = null
  }

  return {
    // 状态
    recordingState,
    analysisResult,
    assessment,
    isAnalyzing,
    error,
    
    // 计算属性
    isRecording,
    isPaused,
    duration,
    audioUrl,
    hasRecording,
    formattedDuration,
    
    // 动作
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    clearRecording,
    analyzeRecording,
    getAnalyser,
    clearError,
  }
})