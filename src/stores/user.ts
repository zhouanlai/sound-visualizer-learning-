import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { learningRecordApi, userProgressApi } from '@/api'
import type { UserProgress, LearningRecord, Achievement } from '@/types'

// addLearningRecord 入参：录音二进制 + 评估结果
export interface AddLearningRecordPayload {
  unitId: string
  pinyin: string
  character: string
  score: number
  accuracy: number
  fluency: number
  pronunciation: number
  duration: number
  feedback?: string
  audioBlob: Blob
}

export const useUserStore = defineStore('user', () => {
  // 状态
  const userId = ref<string>('default_user')
  const username = ref<string>('学习者')
  const progress = ref<UserProgress | null>(null)
  const learningRecords = ref<LearningRecord[]>([])
  const achievements = ref<Achievement[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const totalProgress = computed(() => {
    if (!progress.value) return 0
    return Math.round((progress.value.completedUnits / progress.value.totalUnits) * 100)
  })

  const recentRecords = computed(() => {
    return learningRecords.value
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 10)
  })

  const averageScore = computed(() => {
    if (learningRecords.value.length === 0) return 0
    const sum = learningRecords.value.reduce((acc, record) => acc + record.score, 0)
    return Math.round(sum / learningRecords.value.length)
  })

  const completedUnits = computed(() => {
    if (!progress.value) return 0
    return progress.value.completedUnits
  })

  const totalPracticeCount = computed(() => {
    if (!progress.value) return 0
    return progress.value.totalPractice
  })

  // 动作
  async function fetchProgress() {
    isLoading.value = true
    error.value = null

    try {
      // 真实后端调用：读 SQLite 用户进度
      const res = await userProgressApi.getByUser(userId.value)
      progress.value = res.data
    } catch (err) {
      error.value = '获取进度失败'
      console.error(err)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchLearningRecords() {
    isLoading.value = true
    error.value = null

    try {
      // 真实后端调用：读 SQLite 学习记录（不含音频 BLOB）
      const res = await learningRecordApi.getByUser(userId.value)
      learningRecords.value = res.data
    } catch (err) {
      error.value = '获取学习记录失败'
      console.error(err)
    } finally {
      isLoading.value = false
    }
  }

  async function addLearningRecord(payload: AddLearningRecordPayload) {
    isLoading.value = true
    error.value = null

    try {
      // 真实后端调用：录音二进制(multipart) + 评估结果一并落库，后端同事务更新进度
      const res = await learningRecordApi.create({
        userId: userId.value,
        unitId: payload.unitId,
        pinyin: payload.pinyin,
        character: payload.character,
        score: payload.score,
        accuracy: payload.accuracy,
        fluency: payload.fluency,
        pronunciation: payload.pronunciation,
        duration: payload.duration,
        feedback: payload.feedback ?? '',
        audio: payload.audioBlob,
      })

      if (res.code !== 200) {
        throw new Error(res.message || '保存失败')
      }

      // 落库成功后拉取最新记录与进度，保持 store 与数据库一致
      await Promise.all([fetchLearningRecords(), fetchProgress()])

      // 检查成就
      checkAchievements()
    } catch (err) {
      error.value = '添加学习记录失败'
      console.error(err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function checkAchievements() {
    const newAchievements: Achievement[] = []
    
    // 检查首次练习成就
    if (learningRecords.value.length === 1) {
      newAchievements.push({
        id: 'first_practice',
        name: '初次尝试',
        description: '完成第一次发音练习',
        icon: '🎯',
        condition: '完成第一次练习',
        unlockedAt: new Date().toISOString(),
      })
    }
    
    // 检查连续练习成就
    if (learningRecords.value.length >= 7) {
      const last7Days = learningRecords.value.slice(0, 7)
      const uniqueDays = new Set(
        last7Days.map(r => new Date(r.createdAt).toDateString())
      )
      
      if (uniqueDays.size >= 7) {
        newAchievements.push({
          id: 'week_streak',
          name: '坚持一周',
          description: '连续7天进行发音练习',
          icon: '🔥',
          condition: '连续7天练习',
          unlockedAt: new Date().toISOString(),
        })
      }
    }
    
    // 检查高分成就
    const highScoreRecords = learningRecords.value.filter(r => r.score >= 90)
    if (highScoreRecords.length >= 3) {
      newAchievements.push({
        id: 'high_scorer',
        name: '发音达人',
        description: '获得3次90分以上的成绩',
        icon: '⭐',
        condition: '获得3次90分以上',
        unlockedAt: new Date().toISOString(),
      })
    }
    
    // 添加新成就（避免重复）
    newAchievements.forEach(newAchievement => {
      if (!achievements.value.find(a => a.id === newAchievement.id)) {
        achievements.value.push(newAchievement)
      }
    })
  }

  function clearError() {
    error.value = null
  }

  return {
    // 状态
    userId,
    username,
    progress,
    learningRecords,
    achievements,
    isLoading,
    error,
    
    // 计算属性
    totalProgress,
    recentRecords,
    averageScore,
    completedUnits,
    totalPracticeCount,
    
    // 动作
    fetchProgress,
    fetchLearningRecords,
    addLearningRecord,
    clearError,
  }
})