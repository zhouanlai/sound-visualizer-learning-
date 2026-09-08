import type {
  PronunciationUnit,
  LearningRecord,
  UserProgress,
  PronunciationAssessment,
  AdminStats,
  ApiResponse,
  PaginatedResponse,
  SearchParams,
  MediaAsset,
  CmsUnit,
  UserFeedbackItem,
} from '@/types'

// API基础配置
const API_BASE_URL = 'http://localhost:8000/api'

// 通用请求函数
async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const isFormData = options.body instanceof FormData
  const response = await fetch(`${API_BASE_URL}${url}`, {
    headers: {
      // FormData 时不设置 Content-Type，让浏览器自动带上 boundary
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return response.json()
}

// 发音单元API
export const pronunciationUnitApi = {
  // 获取所有发音单元
  getAll(params?: SearchParams): Promise<ApiResponse<PaginatedResponse<PronunciationUnit>>> {
    const queryString = params ? '?' + new URLSearchParams(params as any).toString() : ''
    return request(`/pronunciation-units${queryString}`)
  },

  // 获取单个发音单元
  getById(id: string): Promise<ApiResponse<PronunciationUnit>> {
    return request(`/pronunciation-units/${id}`)
  },

  // 创建发音单元
  create(unit: Omit<PronunciationUnit, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<PronunciationUnit>> {
    return request('/pronunciation-units', {
      method: 'POST',
      body: JSON.stringify(unit),
    })
  },

  // 更新发音单元
  update(id: string, unit: Partial<PronunciationUnit>): Promise<ApiResponse<PronunciationUnit>> {
    return request(`/pronunciation-units/${id}`, {
      method: 'PUT',
      body: JSON.stringify(unit),
    })
  },

  // 删除发音单元
  delete(id: string): Promise<ApiResponse<void>> {
    return request(`/pronunciation-units/${id}`, {
      method: 'DELETE',
    })
  },
}

// 创建学习记录的入参（录音 Blob + 评估结果，multipart 上传）
export interface CreateLearningRecordPayload {
  userId: string
  unitId: string
  pinyin: string
  character: string
  score: number
  accuracy: number
  fluency: number
  pronunciation: number
  duration: number
  feedback?: string
  audio: Blob
}

// 学习记录API
export const learningRecordApi = {
  // 获取用户学习记录（不含音频，音频按 audioUrl 单独拉取）
  getByUser(userId: string, limit = 20): Promise<ApiResponse<LearningRecord[]>> {
    return request(`/users/${userId}/learning-records?limit=${limit}`)
  },

  // 创建学习记录：录音二进制(multipart) + 评估结果一并落库，后端同事务更新进度
  create(payload: CreateLearningRecordPayload): Promise<ApiResponse<{ id: string }>> {
    const formData = new FormData()
    formData.append('userId', payload.userId)
    formData.append('unitId', payload.unitId)
    formData.append('pinyin', payload.pinyin)
    formData.append('character', payload.character)
    formData.append('score', String(payload.score))
    formData.append('accuracy', String(payload.accuracy))
    formData.append('fluency', String(payload.fluency))
    formData.append('pronunciation', String(payload.pronunciation))
    formData.append('duration', String(payload.duration))
    formData.append('feedback', payload.feedback ?? '')
    formData.append('audio', payload.audio, 'recording.webm')

    return request('/learning-records', {
      method: 'POST',
      body: formData,
    })
  },

  // 获取学习记录详情
  getById(id: string): Promise<ApiResponse<LearningRecord>> {
    return request(`/learning-records/${id}`)
  },

  // 按需拉取录音二进制，返回可播放的 blob URL
  async getRecordAudio(id: string): Promise<string> {
    const response = await fetch(`${API_BASE_URL}/learning-records/${id}/audio`)
    if (!response.ok) {
      throw new Error(`录音加载失败: HTTP ${response.status}`)
    }
    const blob = await response.blob()
    return URL.createObjectURL(blob)
  },

  delete(id: string): Promise<ApiResponse<void>> {
    return request(`/learning-records/${id}`, { method: 'DELETE' })
  },

  deleteAll(userId: string): Promise<ApiResponse<{ deleted: number }>> {
    return request(`/users/${userId}/learning-records`, { method: 'DELETE' })
  },
}

// 用户进度API
export const userProgressApi = {
  // 获取用户进度
  getByUser(userId: string): Promise<ApiResponse<UserProgress>> {
    return request(`/users/${userId}/progress`)
  },

  // 更新用户进度
  update(userId: string, progress: Partial<UserProgress>): Promise<ApiResponse<UserProgress>> {
    return request(`/users/${userId}/progress`, {
      method: 'POST',
      body: JSON.stringify(progress),
    })
  },
}

// 后台管理API
export const adminApi = {
  getAllLearningRecords(limit = 100): Promise<ApiResponse<LearningRecord[]>> {
    return request(`/admin/learning-records?limit=${limit}`)
  },

  getStats(): Promise<ApiResponse<AdminStats>> {
    return request('/admin/stats')
  },

  getFeedbacks(status = ''): Promise<ApiResponse<UserFeedbackItem[]>> {
    const q = status ? `?status=${encodeURIComponent(status)}` : ''
    return request(`/admin/feedback${q}`)
  },

  updateFeedback(id: string, status: string, handleNote: string): Promise<ApiResponse<void>> {
    return request(`/admin/feedback/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ status, handleNote }),
    })
  },
}

// CMS 发音单元
export const unitsApi = {
  list(status = ''): Promise<ApiResponse<CmsUnit[]>> {
    const q = status ? `?status=${encodeURIComponent(status)}` : ''
    return request(`/units${q}`)
  },

  getById(id: string): Promise<ApiResponse<CmsUnit>> {
    return request(`/units/${id}`)
  },

  create(data: Partial<CmsUnit>): Promise<ApiResponse<{ id: string }>> {
    return request('/units', { method: 'POST', body: JSON.stringify(data) })
  },

  update(id: string, data: Partial<CmsUnit>): Promise<ApiResponse<void>> {
    return request(`/units/${id}`, { method: 'PUT', body: JSON.stringify(data) })
  },

  delete(id: string): Promise<ApiResponse<void>> {
    return request(`/units/${id}`, { method: 'DELETE' })
  },
}

// 用户反馈
export const feedbackApi = {
  submit(payload: {
    userId: string
    type: string
    page: string
    unitId?: string
    rating?: string
    message?: string
  }): Promise<ApiResponse<{ id: string }>> {
    return request('/feedback', { method: 'POST', body: JSON.stringify(payload) })
  },
}

// 收藏
export const favoritesApi = {
  list(userId: string): Promise<ApiResponse<string[]>> {
    return request(`/users/${userId}/favorites`)
  },

  add(userId: string, unitId: string): Promise<ApiResponse<void>> {
    return request(`/users/${userId}/favorites/${unitId}`, { method: 'POST' })
  },

  remove(userId: string, unitId: string): Promise<ApiResponse<void>> {
    return request(`/users/${userId}/favorites/${unitId}`, { method: 'DELETE' })
  },
}

// 音频分析API
export const audioAnalysisApi = {
  // 上传音频进行分析
  analyze(audioFile: File, unitId: string): Promise<ApiResponse<PronunciationAssessment>> {
    const formData = new FormData()
    formData.append('audio', audioFile)
    formData.append('unitId', unitId)

    return request('/audio/analyze', {
      method: 'POST',
      body: formData,
      headers: {}, // 让浏览器自动设置Content-Type
    })
  },

  // 实时分析音频流
  analyzeStream(audioData: ArrayBuffer, unitId: string): Promise<ApiResponse<PronunciationAssessment>> {
    return request('/audio/analyze-stream', {
      method: 'POST',
      body: JSON.stringify({
        audioData: Array.from(new Uint8Array(audioData)),
        unitId,
      }),
    })
  },
}

// 媒体资源API
export const mediaApi = {
  // 上传媒体资源
  upload(file: File, type: string): Promise<ApiResponse<MediaAsset>> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', type)

    return request('/media/upload', {
      method: 'POST',
      body: formData,
      headers: {},
    })
  },

  // 获取媒体资源
  getById(id: string): Promise<ApiResponse<MediaAsset>> {
    return request(`/media/${id}`)
  },

  // 删除媒体资源
  delete(id: string): Promise<ApiResponse<void>> {
    return request(`/media/${id}`, {
      method: 'DELETE',
    })
  },
}

// WebSocket连接管理
export class WebSocketManager {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private listeners: Map<string, Set<(data: any) => void>> = new Map()

  constructor(private url: string) {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.reconnectAttempts = 0
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            this.emit(data.type, data.data)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = () => {
          console.log('WebSocket disconnected')
          this.attemptReconnect()
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          reject(error)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
      
      setTimeout(() => {
        this.connect().catch(() => {})
      }, this.reconnectDelay * this.reconnectAttempts)
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)
  }

  off(event: string, callback: (data: any) => void) {
    this.listeners.get(event)?.delete(callback)
  }

  private emit(event: string, data: any) {
    this.listeners.get(event)?.forEach((callback) => callback(data))
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

// 导出WebSocket管理器实例
export const wsManager = new WebSocketManager('ws://localhost:8000/ws/audio-stream')