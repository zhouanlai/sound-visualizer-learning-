<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useUserStore } from '@/stores/user'
import * as echarts from 'echarts'

const userStore = useUserStore()
const chartRef = ref<HTMLDivElement | null>(null)

onMounted(async () => {
  await userStore.fetchProgress()
  await userStore.fetchLearningRecords()
  await nextTick()
  setTimeout(() => initChart(), 100)
})

function initChart() {
  if (!chartRef.value) return
  const chart = echarts.init(chartRef.value)
  const records = userStore.learningRecords.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
  chart.setOption({
    title: { text: '学习进度趋势', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: records.map(r => new Date(r.createdAt).toLocaleDateString()) },
    yAxis: { type: 'value', name: '评分', max: 100 },
    series: [{ type: 'line', data: records.map(r => r.score), smooth: true, areaStyle: { opacity: 0.3 }, lineStyle: { color: '#409eff', width: 3 }, itemStyle: { color: '#409eff' } }],
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
  })
}
</script>

<template>
  <div class="progress-view">
    <div class="stats-row">
      <el-card v-for="item in [
        { label: '总进度', value: userStore.totalProgress + '%', icon: 'TrendCharts', color: '#409eff' },
        { label: '已学单元', value: userStore.completedUnits + '/12', icon: 'Collection', color: '#67c23a' },
        { label: '练习次数', value: userStore.totalPracticeCount, icon: 'Microphone', color: '#e6a23c' },
        { label: '平均分', value: userStore.averageScore, icon: 'Trophy', color: '#f56c6c' },
      ]" :key="item.label" class="stat-card" shadow="hover">
        <div class="stat-icon" :style="{ background: item.color + '20', color: item.color }"><el-icon :size="24"><component :is="item.icon" /></el-icon></div>
        <div class="stat-info"><div class="stat-value">{{ item.value }}</div><div class="stat-label">{{ item.label }}</div></div>
      </el-card>
    </div>

    <el-card class="chart-card" shadow="hover">
      <div ref="chartRef" style="width: 100%; height: 300px;"></div>
    </el-card>

    <el-card shadow="hover">
      <template #header><span>单元进度</span></template>
      <el-table :data="userStore.progress?.unitProgress || []" stripe>
        <el-table-column prop="pinyin" label="拼音" width="100" />
        <el-table-column label="单元" width="80"><template #default="{ row }">{{ ({ ma:'妈',ba:'八',pa:'趴',ta:'他',yi:'一',wu:'五',yu:'鱼',mao:'猫',gou:'狗',niao:'鸟' } as Record<string, string>)[row.unitId] || row.unitId }}</template></el-table-column>
        <el-table-column prop="bestScore" label="最高分" width="100"><template #default="{ row }"><el-tag :type="row.bestScore >= 80 ? 'success' : row.bestScore > 0 ? 'warning' : 'info'">{{ row.bestScore }}</el-tag></template></el-table-column>
        <el-table-column prop="practiceCount" label="练习次数" width="100" />
        <el-table-column label="状态"><template #default="{ row }"><el-tag :type="row.status === 'completed' ? 'success' : row.status === 'in_progress' ? 'warning' : 'info'">{{ ({ completed: '已完成', in_progress: '学习中', not_started: '未开始' } as Record<string, string>)[row.status] }}</el-tag></template></el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.progress-view { display: flex; flex-direction: column; gap: 20px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card { border-radius: 12px; }
.stat-card :deep(.el-card__body) { display: flex; align-items: center; gap: 16px; padding: 20px; }
.stat-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.stat-value { font-size: 28px; font-weight: 700; color: #303133; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.chart-card { border-radius: 12px; }
</style>