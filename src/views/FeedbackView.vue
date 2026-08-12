<script setup lang="ts">
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRecordingStore } from '@/stores/recording'
import * as echarts from 'echarts'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const route = useRoute()
const router = useRouter()
const recordingStore = useRecordingStore()

const unitId = computed(() => route.params.id as string)
const assessment = computed(() => recordingStore.assessment)

const toneChartRef = ref<HTMLDivElement | null>(null)
const threeContainerRef = ref<HTMLDivElement | null>(null)
const spectrogramRef = ref<HTMLCanvasElement | null>(null)
const formantChartRef = ref<HTMLDivElement | null>(null)
const energyChartRef = ref<HTMLDivElement | null>(null)

// 3D口腔模型
function initThreeScene() {
  if (!threeContainerRef.value) return
  const container = threeContainerRef.value
  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x1a1a2e)
  const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 1000)
  camera.position.set(0, 0, 3)
  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(container.clientWidth, container.clientHeight)
  container.appendChild(renderer.domElement)

  // 灯光
  const ambientLight = new THREE.AmbientLight(0x404040, 2)
  scene.add(ambientLight)
  const dirLight = new THREE.DirectionalLight(0xffffff, 1)
  dirLight.position.set(5, 5, 5)
  scene.add(dirLight)

  // 口腔模型（简化版）
  // 上颚
  const palateGeom = new THREE.SphereGeometry(1, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2)
  const palateMat = new THREE.MeshPhongMaterial({ color: 0xff9999, transparent: true, opacity: 0.6, side: THREE.DoubleSide })
  const palate = new THREE.Mesh(palateGeom, palateMat)
  palate.position.y = 0.3
  scene.add(palate)

  // 舌头
  const tongueGeom = new THREE.SphereGeometry(0.7, 32, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2)
  const tongueMat = new THREE.MeshPhongMaterial({ color: 0xcc3333, transparent: true, opacity: 0.8 })
  const tongue = new THREE.Mesh(tongueGeom, tongueMat)
  tongue.position.y = -0.2
  tongue.scale.set(1, 0.5, 1)
  scene.add(tongue)

  // 牙齿（上）
  const teethGeom = new THREE.TorusGeometry(0.9, 0.05, 8, 32, Math.PI)
  const teethMat = new THREE.MeshPhongMaterial({ color: 0xffffff })
  const teeth = new THREE.Mesh(teethGeom, teethMat)
  teeth.position.y = 0.1
  teeth.rotation.x = Math.PI / 2
  scene.add(teeth)

  // 气流粒子
  const particlesGeom = new THREE.BufferGeometry()
  const particleCount = 200
  const positions = new Float32Array(particleCount * 3)
  for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 0.3
    positions[i * 3 + 1] = Math.random() * 2 - 0.5
    positions[i * 3 + 2] = (Math.random() - 0.5) * 0.3
  }
  particlesGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  const particlesMat = new THREE.PointsMaterial({ color: 0x409eff, size: 0.03, transparent: true, opacity: 0.7 })
  const particles = new THREE.Points(particlesGeom, particlesMat)
  scene.add(particles)

  // 控制器
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true

  // 动画
  let time = 0
  function animate() {
    requestAnimationFrame(animate)
    time += 0.02

    // 舌头动画
    tongue.position.y = -0.2 + Math.sin(time * 2) * 0.05
    tongue.rotation.z = Math.sin(time) * 0.1

    // 气流动画
    const positionAttr = particles.geometry.attributes.position
    if (positionAttr) {
      const pos = positionAttr.array as Float32Array
      for (let i = 0; i < particleCount; i++) {
        const idx = i * 3 + 1
        if (pos[idx] !== undefined) {
          pos[idx] += 0.02
          if (pos[idx] > 1.5) {
            pos[idx] = -0.5
            pos[i * 3] = (Math.random() - 0.5) * 0.3
            pos[i * 3 + 2] = (Math.random() - 0.5) * 0.3
          }
        }
      }
      positionAttr.needsUpdate = true
    }

    controls.update()
    renderer.render(scene, camera)
  }
  animate()
}

// 声调曲线对比图（标准曲线由后端生成）
function initToneChart() {
  if (!toneChartRef.value) return
  const existing = echarts.getInstanceByDom(toneChartRef.value)
  if (existing) existing.dispose()
  const chart = echarts.init(toneChartRef.value)

  const userF0 = assessment.value?.audioAnalysis.f0 || []
  // 标准曲线：优先使用后端返回的 standardF0，无数据时基于识别声调在前端生成兜底曲线
  let standardF0 = assessment.value?.audioAnalysis.standardF0 || []
  if (standardF0.length === 0 && userF0.length > 0) {
    const tone = assessment.value?.audioAnalysis.detectedTone || 1
    standardF0 = userF0.map((_, i) => {
      const t = i / userF0.length
      if (tone === 2) return 120 + t * 80
      if (tone === 3) return 150 - t * 40 + (t > 0.5 ? (t - 0.5) * 120 : 0)
      if (tone === 4) return 220 - t * 80
      return 200 + Math.sin(t * Math.PI) * 5
    })
  }

  const labels = userF0.map((_, i) => i)

  chart.setOption({
    title: { text: '声调曲线对比', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['您的发音', '标准发音'], bottom: 0 },
    xAxis: { type: 'category', data: labels, name: '时间' },
    yAxis: { type: 'value', name: '频率 (Hz)' },
    series: [
      { name: '您的发音', type: 'line', data: userF0, smooth: true, lineStyle: { color: '#409eff', width: 3 }, itemStyle: { color: '#409eff' } },
      { name: '标准发音', type: 'line', data: standardF0, smooth: true, lineStyle: { color: '#67c23a', width: 3, type: 'dashed' }, itemStyle: { color: '#67c23a' } },
    ],
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
  })
}

// 声谱图（语谱图）
function initSpectrogram() {
  if (!spectrogramRef.value) return
  const canvas = spectrogramRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  canvas.width = 500
  canvas.height = 200
  const w = canvas.width
  const h = canvas.height

  // 用后端返回的真实MFCC数据生成频谱图（无假数据回退）
  const timeSteps = 100
  const freqBins = 80
  const mfcc = assessment.value?.audioAnalysis.mfcc || []

  // 若后端未返回MFCC数据，显示空白并标注
  const hasMfcc = mfcc.length > 0 && (mfcc[0]?.length ?? 0) > 0

  for (let t = 0; t < timeSteps; t++) {
    for (let f = 0; f < freqBins; f++) {
      // 用MFCC数据生成能量值
      let energy = 0
      if (hasMfcc) {
        const mfccIdx = Math.floor(f / freqBins * mfcc.length)
        const timeIdx = Math.floor(t / timeSteps * (mfcc[0]?.length || 1))
        energy = Math.abs(mfcc[mfccIdx]?.[timeIdx] || 0)
      } else {
        energy = 0
      }
      energy = Math.max(0, Math.min(1, energy))

      // 颜色映射：深蓝→青→绿→黄→红
      const r = Math.floor(energy < 0.5 ? energy * 2 * 255 : 255)
      const g = Math.floor(energy < 0.5 ? energy * 2 * 255 : (1 - energy) * 2 * 255)
      const b = Math.floor(energy < 0.5 ? 255 : (1 - energy) * 2 * 255)

      ctx.fillStyle = `rgb(${r},${g},${b})`
      ctx.fillRect((t / timeSteps) * w, (1 - f / freqBins) * h, w / timeSteps + 1, h / freqBins + 1)
    }
  }

  // 坐标轴标签
  ctx.fillStyle = '#909399'
  ctx.font = '11px sans-serif'
  ctx.fillText('时间 →', w - 50, h - 5)
  ctx.save()
  ctx.translate(12, h / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('频率 →', -20, 0)
  ctx.restore()
}

// 共振峰轨迹图 (F1-F2空间)
function initFormantChart() {
  if (!formantChartRef.value) return
  const existing = echarts.getInstanceByDom(formantChartRef.value)
  if (existing) existing.dispose()
  const chart = echarts.init(formantChartRef.value)

  const f1Data = assessment.value?.audioAnalysis.f1 || []
  const f2Data = assessment.value?.audioAnalysis.f2 || []

  // 采样减少点数
  const step = Math.max(1, Math.floor(f1Data.length / 30))
  const scatterData: number[][] = []
  for (let i = 0; i < f1Data.length; i += step) {
    scatterData.push([f2Data[i] ?? 0, f1Data[i] ?? 0])
  }

  // 标准元音位置 (F2, F1)
  const standardVowels: [string, number[]][] = [
    ['i', [2400, 280]], ['e', [2100, 400]], ['a', [1100, 750]],
    ['o', [800, 500]], ['u', [600, 300]],
  ]

  chart.setOption({
    title: { text: '共振峰轨迹图 (F1-F2)', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      formatter: (p: any) => {
        if (p.seriesIndex === 0) return `F1: ${p.data[1].toFixed(0)} Hz<br/>F2: ${p.data[0].toFixed(0)} Hz`
        return p.name
      },
    },
    xAxis: { type: 'value', name: 'F2 (Hz)', inverse: true, min: 500, max: 2500 },
    yAxis: { type: 'value', name: 'F1 (Hz)', inverse: true, min: 200, max: 900 },
    series: [
      {
        name: '您的发音',
        type: 'line',
        data: scatterData,
        smooth: true,
        lineStyle: { color: '#409eff', width: 3 },
        itemStyle: { color: '#409eff' },
        symbolSize: 6,
      },
      {
        name: '标准元音',
        type: 'scatter',
        data: standardVowels.map(v => ({ value: v[1], name: v[0] })),
        symbolSize: 14,
        itemStyle: { color: '#67c23a' },
        label: { show: true, formatter: '{b}', position: 'right', fontSize: 12 },
      },
    ],
    legend: { data: ['您的发音', '标准元音'], bottom: 0 },
    grid: { left: 60, right: 40, top: 40, bottom: 40 },
  })
}

// 能量包络图
function initEnergyChart() {
  if (!energyChartRef.value) return
  const existing = echarts.getInstanceByDom(energyChartRef.value)
  if (existing) existing.dispose()
  const chart = echarts.init(energyChartRef.value)

  const energy = assessment.value?.audioAnalysis.energy || []
  const labels = energy.map((_, i) => i)
  const duration = assessment.value?.audioAnalysis.duration || 1.5

  chart.setOption({
    title: { text: '能量包络图', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis', formatter: (p: any) => `时间: ${(p[0].dataIndex / energy.length * duration).toFixed(2)}s<br/>能量: ${p[0].data.toFixed(3)}` },
    xAxis: {
      type: 'category',
      data: labels,
      name: '时间',
      axisLabel: { formatter: (v: string) => (parseInt(v) / energy.length * duration).toFixed(1) + 's' },
    },
    yAxis: { type: 'value', name: '能量', min: 0, max: 1 },
    series: [{
      type: 'line',
      data: energy,
      smooth: true,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.6)' },
          { offset: 1, color: 'rgba(64,158,255,0.05)' },
        ]),
      },
      lineStyle: { color: '#409eff', width: 2 },
      itemStyle: { color: '#409eff' },
      symbol: 'none',
    }],
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
  })
}

const scoreColor = computed(() => {
  const s = assessment.value?.score || 0
  if (s >= 80) return '#67c23a'
  if (s >= 60) return '#e6a23c'
  return '#f56c6c'
})

// 数据图表统一渲染（声调/声谱/共振峰/能量），重绘前已做 dispose 防护
function renderDataCharts() {
  initToneChart()
  initSpectrogram()
  initFormantChart()
  initEnergyChart()
}

onMounted(async () => {
  // 等待DOM渲染完成后再初始化图表
  await nextTick()
  setTimeout(() => {
    renderDataCharts()
    initThreeScene()
  }, 100)
})

// 当后端分析结果到达（可能晚于组件挂载）时重绘数据图表，避免空白
watch(
  () => assessment.value?.audioAnalysis,
  (val) => {
    if (val && (val.f0?.length || val.energy?.length || val.mfcc?.length)) {
      nextTick(() => renderDataCharts())
    }
  }
)
</script>

<template>
  <div class="feedback-view">
    <!-- 综合评分 -->
    <div class="score-section">
      <div class="score-ring">
        <el-progress type="circle" :percentage="Math.round(assessment?.score || 0)" :color="scoreColor" :width="140" :stroke-width="12">
          <template #default="{ percentage }">
            <div class="score-inner">
              <span class="score-number">{{ percentage }}</span>
              <span class="score-label">综合评分</span>
            </div>
          </template>
        </el-progress>
      </div>
      <div class="score-detail">
        <div class="score-item"><span>准确度</span><el-progress :percentage="Math.round(assessment?.accuracy || 0)" :color="'#409eff'" /></div>
        <div class="score-item"><span>流利度</span><el-progress :percentage="Math.round(assessment?.fluency || 0)" :color="'#67c23a'" /></div>
        <div class="score-item"><span>发音</span><el-progress :percentage="Math.round(assessment?.pronunciation || 0)" :color="'#e6a23c'" /></div>
      </div>
    </div>

    <!-- 音素级分析（深度学习识别结果） -->
    <div class="phoneme-section" v-if="assessment?.audioAnalysis.phonemes?.length">
      <h3>音素级分析 <small>基于 Wav2Vec2 深度学习模型识别</small></h3>
      <div class="phoneme-list">
        <div v-for="(p, idx) in assessment.audioAnalysis.phonemes" :key="idx" class="phoneme-item" :class="p.score >= 80 ? 'good' : (p.score >= 60 ? 'warn' : 'bad')">
          <div class="phoneme-name">{{ p.phoneme }}</div>
          <div class="phoneme-compare">
            <span class="expected">目标：{{ p.expected }}</span>
            <span class="arrow">→</span>
            <span class="detected">识别：{{ p.detected }}</span>
          </div>
          <div class="phoneme-score">
            <el-progress :percentage="Math.round(p.score)" :stroke-width="10" :color="p.score >= 80 ? '#67c23a' : (p.score >= 60 ? '#e6a23c' : '#f56c6c')" />
          </div>
          <p class="phoneme-feedback">{{ p.feedback }}</p>
        </div>
      </div>
      <div class="phoneme-summary" v-if="assessment.audioAnalysis.recognizedText">
        <span class="label">识别文本：</span>
        <span class="value">{{ assessment.audioAnalysis.recognizedText }}</span>
        <span class="label">识别声调：</span>
        <span class="value">第{{ assessment.audioAnalysis.detectedTone || '（依据F0判定）' }}声</span>
      </div>
    </div>

    <!-- 声调曲线 + 3D动画 -->
    <div class="analysis-row">
      <div class="chart-card">
        <div ref="toneChartRef" class="chart-container"></div>
      </div>
      <div class="three-card">
        <h4>3D发音动画 <small>（拖拽旋转，滚轮缩放）</small></h4>
        <div ref="threeContainerRef" class="three-container"></div>
      </div>
    </div>

    <!-- 声谱图 + 共振峰 + 能量图 -->
    <div class="analysis-row three-col">
      <div class="chart-card">
        <h4>声谱图（语谱图）</h4>
        <canvas ref="spectrogramRef" class="spectrogram-canvas"></canvas>
        <p class="chart-desc">颜色越亮表示该频率在该时间点的能量越强</p>
      </div>
      <div class="chart-card">
        <div ref="formantChartRef" class="chart-container"></div>
      </div>
      <div class="chart-card">
        <div ref="energyChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- 反馈建议 -->
    <div class="feedback-section">
      <h3>改进建议</h3>
      <div class="feedback-list">
        <div v-for="(item, idx) in (assessment?.feedback || [])" :key="idx" class="feedback-item" :class="item.type">
          <el-icon v-if="item.type === 'error'" color="#f56c6c"><CircleCloseFilled /></el-icon>
          <el-icon v-else-if="item.type === 'warning'" color="#e6a23c"><WarningFilled /></el-icon>
          <el-icon v-else color="#409eff"><InfoFilled /></el-icon>
          <div>
            <strong>{{ item.message }}</strong>
            <p>{{ item.detail }}</p>
            <p class="improvement">💡 {{ item.improvement }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <el-button :icon="'Refresh'" size="large" @click="router.push(`/learn/${unitId}`)">重新录音</el-button>
      <el-button type="primary" :icon="'Back'" size="large" @click="router.push('/library')">返回发音库</el-button>
    </div>
  </div>
</template>

<style scoped>
.feedback-view { display: flex; flex-direction: column; gap: 20px; }
.score-section { background: white; border-radius: 12px; padding: 24px; display: flex; align-items: center; gap: 40px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.score-ring { flex-shrink: 0; }
.score-inner { text-align: center; }
.score-number { font-size: 36px; font-weight: 700; color: #303133; display: block; }
.score-label { font-size: 12px; color: #909399; }
.score-detail { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.score-item { display: flex; align-items: center; gap: 12px; }
.score-item span { width: 60px; font-size: 14px; color: #606266; }
.analysis-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.analysis-row.three-col { grid-template-columns: 1fr 1fr 1fr; }
.spectrogram-canvas { width: 100%; height: 200px; border-radius: 8px; background: #0a0a1a; }
.chart-desc { font-size: 11px; color: #909399; text-align: center; margin-top: 6px; }
.chart-card h4 { margin: 0 0 8px; font-size: 14px; color: #303133; }
.chart-card, .three-card { background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.chart-container { width: 100%; height: 300px; }
.three-card h4 { margin: 0 0 8px; font-size: 14px; color: #303133; }
.three-card h4 small { font-size: 11px; color: #909399; font-weight: normal; }
.three-container { width: 100%; height: 300px; border-radius: 8px; overflow: hidden; }
.phoneme-section { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.phoneme-section h3 { margin: 0 0 16px; font-size: 16px; color: #303133; }
.phoneme-section h3 small { font-size: 12px; color: #909399; font-weight: normal; }
.phoneme-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.phoneme-item { border-radius: 8px; padding: 14px; border: 1px solid #e4e7ed; }
.phoneme-item.good { border-color: #b3e19d; background: #f0f9eb; }
.phoneme-item.warn { border-color: #f3d19e; background: #fdf6ec; }
.phoneme-item.bad { border-color: #fbc4c4; background: #fef0f0; }
.phoneme-name { font-weight: 700; color: #303133; margin-bottom: 8px; font-size: 14px; }
.phoneme-compare { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #606266; margin-bottom: 8px; }
.phoneme-compare .arrow { color: #c0c4cc; }
.phoneme-score { margin-bottom: 6px; }
.phoneme-feedback { margin: 0; font-size: 12px; color: #909399; }
.phoneme-summary { margin-top: 16px; padding: 12px 16px; background: #ecf5ff; border-radius: 8px; font-size: 13px; color: #303133; }
.phoneme-summary .label { color: #909399; margin-right: 4px; }
.phoneme-summary .value { font-weight: 500; margin-right: 20px; }
.feedback-section { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.feedback-section h3 { margin: 0 0 16px; font-size: 16px; color: #303133; }
.feedback-list { display: flex; flex-direction: column; gap: 12px; }
.feedback-item { display: flex; gap: 12px; align-items: flex-start; padding: 16px; border-radius: 8px; background: #f5f7fa; }
.feedback-item.error { background: #fef0f0; }
.feedback-item.warning { background: #fdf6ec; }
.feedback-item.suggestion { background: #ecf5ff; }
.feedback-item strong { color: #303133; display: block; margin-bottom: 4px; }
.feedback-item p { margin: 2px 0; color: #606266; font-size: 13px; }
.improvement { color: #409eff !important; font-weight: 500; }
.action-bar { display: flex; justify-content: center; gap: 16px; padding: 16px 0; }
</style>