<script setup lang="ts">
import { ref } from 'vue'

const leftRecording = ref(false)
const rightRecording = ref(false)
const leftAudioUrl = ref<string | null>(null)
const rightAudioUrl = ref<string | null>(null)
const comparing = ref(false)
const similarity = ref(0)

async function toggleRecord(side: 'left' | 'right') {
  const isRecording = side === 'left' ? leftRecording : rightRecording
  if (isRecording.value) {
    isRecording.value = false
    if (side === 'left') leftAudioUrl.value = 'mock-url'
    else rightAudioUrl.value = 'mock-url'
  } else {
    isRecording.value = true
  }
}

function doCompare() {
  comparing.value = true
  setTimeout(() => { similarity.value = 72 + Math.floor(Math.random() * 20); comparing.value = false }, 2000)
}
</script>

<template>
  <div class="comparison-view">
    <h3>发音对比</h3>
    <p class="desc">录制两段发音进行对比分析</p>
    <div class="compare-grid">
      <el-card class="compare-card" shadow="hover">
        <h4>发音 A</h4>
        <div class="record-area">
          <el-button :type="leftRecording ? 'danger' : 'primary'" :icon="'Microphone'" circle size="large" @click="toggleRecord('left')" />
          <span>{{ leftRecording ? '录音中...' : leftAudioUrl ? '已录制' : '点击录音' }}</span>
        </div>
      </el-card>
      <div class="compare-center">
        <el-button type="primary" :icon="'Switch'" :loading="comparing" @click="doCompare" :disabled="!leftAudioUrl || !rightAudioUrl">开始对比</el-button>
        <div v-if="similarity > 0" class="similarity">
          <el-progress type="circle" :percentage="similarity" :color="similarity >= 80 ? '#67c23a' : similarity >= 60 ? '#e6a23c' : '#f56c6c'" :width="100" />
          <span>相似度</span>
        </div>
      </div>
      <el-card class="compare-card" shadow="hover">
        <h4>发音 B</h4>
        <div class="record-area">
          <el-button :type="rightRecording ? 'danger' : 'primary'" :icon="'Microphone'" circle size="large" @click="toggleRecord('right')" />
          <span>{{ rightRecording ? '录音中...' : rightAudioUrl ? '已录制' : '点击录音' }}</span>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.comparison-view { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.comparison-view h3 { margin: 0; font-size: 20px; color: #303133; }
.desc { color: #909399; margin: 8px 0 24px; }
.compare-grid { display: grid; grid-template-columns: 1fr auto 1fr; gap: 24px; align-items: center; }
.compare-card { border-radius: 12px; text-align: center; }
.compare-card h4 { margin: 0 0 20px; }
.record-area { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 0; }
.compare-center { display: flex; flex-direction: column; align-items: center; gap: 20px; }
.similarity { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.similarity span { font-size: 13px; color: #909399; }
</style>