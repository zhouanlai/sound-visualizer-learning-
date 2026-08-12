<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useUserStore } from '@/stores/user'
import * as echarts from 'echarts'

const userStore = useUserStore()
const activeTab = ref('overview')
const trendChartRef = ref<HTMLDivElement | null>(null)

onMounted(async () => {
  await userStore.fetchProgress()
  await userStore.fetchLearningRecords()
  await nextTick()
  setTimeout(() => initTrendChart(), 100)
})

function initTrendChart() {
  if (!trendChartRef.value) return
  const chart = echarts.init(trendChartRef.value)
  const records = userStore.learningRecords.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
  chart.setOption({
    title: { text: '学习趋势', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: records.map(r => new Date(r.createdAt).toLocaleDateString()) },
    yAxis: { type: 'value', max: 100 },
    series: [
      { name: '评分', type: 'line', data: records.map(r => r.score), smooth: true, lineStyle: { color: '#409eff' }, itemStyle: { color: '#409eff' } },
      { name: '准确度', type: 'line', data: records.map(r => r.accuracy), smooth: true, lineStyle: { color: '#67c23a' }, itemStyle: { color: '#67c23a' } },
    ],
    legend: { bottom: 0 },
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
  })
}

const achievements = [
  { name: '初次尝试', desc: '完成第一次发音练习', icon: '🎯', unlocked: true },
  { name: '坚持一周', desc: '连续7天练习', icon: '🔥', unlocked: false },
  { name: '发音达人', desc: '获得3次90分以上', icon: '⭐', unlocked: false },
  { name: '完美发音', desc: '单次获得100分', icon: '💎', unlocked: false },
]
</script>

<template>
  <div class="progress-mgmt">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="概览" name="overview">
        <div class="overview-cards">
          <el-card v-for="item in [
            { label: '总进度', value: userStore.totalProgress + '%', color: '#409eff' },
            { label: '已学单元', value: userStore.completedUnits + '/12', color: '#67c23a' },
            { label: '练习次数', value: String(userStore.totalPracticeCount), color: '#e6a23c' },
            { label: '平均分', value: String(userStore.averageScore), color: '#f56c6c' },
          ]" :key="item.label" shadow="hover" class="overview-card">
            <div class="ov-value" :style="{ color: item.color }">{{ item.value }}</div>
            <div class="ov-label">{{ item.label }}</div>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="单元详情" name="units">
        <el-card shadow="hover">
          <el-table :data="userStore.progress?.unitProgress || []" stripe>
            <el-table-column prop="pinyin" label="拼音" width="100" />
            <el-table-column prop="bestScore" label="最高分" width="100"><template #default="{ row }"><el-progress :percentage="row.bestScore" :color="row.bestScore >= 80 ? '#67c23a' : '#409eff'" :stroke-width="8" /></template></el-table-column>
            <el-table-column prop="practiceCount" label="练习次数" width="100" />
            <el-table-column label="状态"><template #default="{ row }"><el-tag :type="row.status === 'completed' ? 'success' : row.status === 'in_progress' ? 'warning' : 'info'">{{ ({ completed: '已完成', in_progress: '学习中', not_started: '未开始' } as Record<string, string>)[row.status] }}</el-tag></template></el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="趋势" name="trend">
        <el-card shadow="hover"><div ref="trendChartRef" style="width:100%;height:350px;"></div></el-card>
      </el-tab-pane>

      <el-tab-pane label="成就" name="achievements">
        <div class="achievement-grid">
          <el-card v-for="a in achievements" :key="a.name" shadow="hover" class="achievement-card" :class="{ locked: !a.unlocked }">
            <div class="ach-icon">{{ a.icon }}</div>
            <div class="ach-name">{{ a.name }}</div>
            <div class="ach-desc">{{ a.desc }}</div>
            <el-tag :type="a.unlocked ? 'success' : 'info'" size="small">{{ a.unlocked ? '已解锁' : '未解锁' }}</el-tag>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.progress-mgmt { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.overview-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.overview-card { text-align: center; border-radius: 12px; }
.ov-value { font-size: 36px; font-weight: 700; }
.ov-label { font-size: 14px; color: #909399; margin-top: 4px; }
.achievement-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
.achievement-card { text-align: center; border-radius: 12px; transition: all 0.3s; }
.achievement-card.locked { opacity: 0.5; filter: grayscale(1); }
.ach-icon { font-size: 48px; margin-bottom: 8px; }
.ach-name { font-size: 16px; font-weight: 600; color: #303133; }
.ach-desc { font-size: 12px; color: #909399; margin: 4px 0 12px; }
</style>