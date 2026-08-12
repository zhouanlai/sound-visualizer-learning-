<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { learningRecordApi } from '@/api'
import { useRouter } from 'vue-router'
import type { LearningRecord } from '@/types'

const userStore = useUserStore()
const router = useRouter()

onMounted(async () => {
  await userStore.fetchLearningRecords()
})

function getScoreType(score: number) {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

async function replayAudio(record: LearningRecord) {
  try {
    // 从数据库按需拉取录音二进制，转 blob URL 播放
    const url = await learningRecordApi.getRecordAudio(record.id)
    const audio = new Audio(url)
    audio.play().catch(() => {})
  } catch (err) {
    ElMessage.error('录音加载失败')
    console.error(err)
  }
}
</script>

<template>
  <div class="history-view">
    <div class="stats-cards">
      <el-card v-for="item in [
        { label: '学习单元', value: userStore.completedUnits, icon: 'Collection' },
        { label: '练习次数', value: userStore.totalPracticeCount, icon: 'Microphone' },
        { label: '平均分', value: userStore.averageScore, icon: 'TrendCharts' },
      ]" :key="item.label" shadow="hover" class="stat-card">
        <el-icon :size="20" color="#409eff"><component :is="item.icon" /></el-icon>
        <div><div class="val">{{ item.value }}</div><div class="lbl">{{ item.label }}</div></div>
      </el-card>
    </div>

    <el-card shadow="hover" class="table-card">
      <template #header><span>学习记录</span></template>
      <el-table :data="userStore.learningRecords" stripe>
        <el-table-column label="时间" width="180"><template #default="{ row }">{{ new Date(row.createdAt).toLocaleString() }}</template></el-table-column>
        <el-table-column label="拼音" width="100"><template #default="{ row }"><span class="pinyin-tag">{{ row.pinyinTone || row.pinyin }}</span></template></el-table-column>
        <el-table-column label="汉字" width="80"><template #default="{ row }">{{ row.character }}</template></el-table-column>
        <el-table-column label="评分" width="100"><template #default="{ row }"><el-tag :type="getScoreType(row.score)">{{ row.score }}</el-tag></template></el-table-column>
        <el-table-column label="准确度" width="100"><template #default="{ row }">{{ row.accuracy }}%</template></el-table-column>
        <el-table-column label="反馈" prop="feedback" show-overflow-tooltip />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" :icon="'VideoPlay'" @click="replayAudio(row)">重听</el-button>
            <el-button size="small" type="primary" :icon="'Refresh'" @click="router.push(`/learn/${row.unitId}`)">重练</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.history-view { display: flex; flex-direction: column; gap: 20px; }
.stats-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.stat-card :deep(.el-card__body) { display: flex; align-items: center; gap: 12px; }
.val { font-size: 24px; font-weight: 700; color: #303133; }
.lbl { font-size: 13px; color: #909399; }
.pinyin-tag { color: #409eff; font-weight: 600; }
.table-card { border-radius: 12px; }
</style>