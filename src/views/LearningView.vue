<script setup lang="ts">
import { ref, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useRecordingStore } from '@/stores/recording'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const recordingStore = useRecordingStore()
const userStore = useUserStore()

const unitData: Record<string, any> = {
  ma: { pinyin: 'mā', character: '妈', tone: 1, desc: '双唇鼻音，第一声（阴平）', detail: '双唇紧闭，软腭下降，打开鼻腔通路，声带振动。声调保持高平。' },
  ba: { pinyin: 'bā', character: '八', tone: 1, desc: '双唇清塞音，第一声', detail: '双唇紧闭，然后突然打开，气流冲出。不送气。' },
  pa: { pinyin: 'pā', character: '趴', tone: 1, desc: '双唇清塞音，第一声', detail: '双唇紧闭，然后突然打开，气流冲出。送气。' },
  ta: { pinyin: 'tā', character: '他', tone: 1, desc: '舌尖中清塞音，第一声', detail: '舌尖抵住上齿龈，然后突然放开。' },
  yi: { pinyin: 'yī', character: '一', tone: 1, desc: '齐齿呼，第一声', detail: '口微开，上下齿对齐，舌面前部接近硬腭。' },
  wu: { pinyin: 'wǔ', character: '五', tone: 3, desc: '合口呼，第三声', detail: '双唇拢圆，舌面后部隆起。声调先降后升。' },
  yu: { pinyin: 'yú', character: '鱼', tone: 2, desc: '撮口呼，第二声', detail: '双唇拢圆，舌面前部接近硬腭。声调上升。' },
  mao: { pinyin: 'māo', character: '猫', tone: 1, desc: '双唇鼻音+复韵母', detail: '先发m音，然后滑向ao。' },
  gou: { pinyin: 'gǒu', character: '狗', tone: 3, desc: '舌根音+复韵母', detail: '舌根抵住软腭，然后放开，滑向ou。' },
  niao: { pinyin: 'niǎo', character: '鸟', tone: 3, desc: '舌尖中音+复韵母', detail: '舌尖抵住上齿龈，鼻音，滑向iao。' },
  ma_t2: { pinyin: 'má', character: '麻', tone: 2, desc: '双唇鼻音，第二声（阳平）', detail: '声调从中音升到高音。' },
  ma_t3: { pinyin: 'mǎ', character: '马', tone: 3, desc: '双唇鼻音，第三声（上声）', detail: '声调先降后升。' },
}

const unitId = computed(() => route.params.id as string)
const unit = computed(() => unitData[unitId.value] || unitData.ma)
const isPlaying = ref(false)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const pitchHistory = ref<number[]>([])
let animationFrame: number | null = null

function playDemo() {
  if (!('speechSynthesis' in window)) {
    alert('您的浏览器不支持语音合成功能')
    return
  }
  isPlaying.value = true
  // 取消之前的语音
  speechSynthesis.cancel()
  
  const utterance = new SpeechSynthesisUtterance(unit.value.character)
  utterance.lang = 'zh-CN'
  utterance.rate = 0.8 // 稍慢，方便学习
  utterance.pitch = 1.0
  utterance.volume = 1.0
  
  // 尝试选择中文语音
  const voices = speechSynthesis.getVoices()
  const zhVoice = voices.find(v => v.lang.startsWith('zh'))
  if (zhVoice) utterance.voice = zhVoice
  
  utterance.onend = () => { isPlaying.value = false }
  utterance.onerror = () => { isPlaying.value = false }
  speechSynthesis.speak(utterance)
}

async function startRecording() {
  await recordingStore.startRecording()
  startVisualization()
}

function stopRecording() {
  recordingStore.stopRecording()
  stopVisualization()
}

function startVisualization() {
  const analyser = recordingStore.getAnalyser()
  if (!analyser || !canvasRef.value) return
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const safeAnalyser = analyser
  const bufLen = safeAnalyser.frequencyBinCount
  const data = new Uint8Array(bufLen)
  function draw() {
    animationFrame = requestAnimationFrame(draw)
    safeAnalyser.getByteTimeDomainData(data)
    ctx!.fillStyle = '#1a1a2e'
    ctx!.fillRect(0, 0, canvas.width, canvas.height)
    ctx!.lineWidth = 2; ctx!.strokeStyle = '#409eff'; ctx!.beginPath()
    const sw = canvas.width / bufLen; let x = 0
    for (let i = 0; i < bufLen; i++) {
      const y = ((data[i] ?? 128) / 128.0) * canvas.height / 2
      i === 0 ? ctx!.moveTo(x, y) : ctx!.lineTo(x, y)
      x += sw
    }
    ctx!.lineTo(canvas.width, canvas.height / 2); ctx!.stroke()
  }
  draw()
}

function stopVisualization() {
  if (animationFrame) { cancelAnimationFrame(animationFrame); animationFrame = null }
}

async function analyzeAndGoFeedback() {
  stopRecording()
  await recordingStore.analyzeRecording(unitId.value)
  const assessment = recordingStore.assessment
  // 自动保存：录音二进制 + 评估结果一并写入数据库，并联动更新学习进度/记录
  try {
    await userStore.addLearningRecord({
      unitId: unitId.value,
      pinyin: unit.value.pinyin,
      character: unit.value.character,
      score: assessment?.score || 0,
      accuracy: assessment?.accuracy || 0,
      fluency: assessment?.fluency || 0,
      pronunciation: assessment?.pronunciation || 0,
      duration: recordingStore.duration,
      feedback: assessment?.feedback.map(f => f.message).join('; ') || '',
      audioBlob: recordingStore.recordingState.audioBlob ?? new Blob(),
    })
  } catch (err) {
    // 保存失败不阻塞反馈展示，但明确提示
    ElMessage.error('学习记录保存失败，请确认后端服务已启动')
  }
  router.push(`/feedback/${unitId.value}`)
}

onUnmounted(() => { stopVisualization() })
</script>

<template>
  <div class="learning-view">
    <!-- 顶部：发音教学区 -->
    <div class="teaching-section">
      <div class="unit-info">
        <div class="unit-character">{{ unit.character }}</div>
        <div class="unit-pinyin">{{ unit.pinyin }}</div>
        <div class="unit-desc">{{ unit.desc }}</div>
        <p class="unit-detail">{{ unit.detail }}</p>
      </div>
      <div class="teaching-actions">
        <el-button type="primary" :icon="'VideoPlay'" @click="playDemo" :loading="isPlaying">
          {{ isPlaying ? '播放中...' : '播放示范' }}
        </el-button>
        <el-button :icon="'VideoPause'">慢速播放</el-button>
      </div>
    </div>

    <!-- 中部：录音练习区 -->
    <div class="recording-section">
      <h3>录音练习</h3>
      <div class="recording-controls">
        <el-button
          v-if="!recordingStore.isRecording"
          type="danger"
          :icon="'Microphone'"
          size="large"
          circle
          @click="startRecording"
          class="record-btn"
        />
        <el-button
          v-else
          type="info"
          :icon="'VideoPause'"
          size="large"
          circle
          @click="stopRecording"
          class="record-btn recording"
        />
        <span class="record-time">{{ recordingStore.formattedDuration }}</span>
      </div>
      <canvas ref="canvasRef" width="600" height="120" class="waveform-canvas"></canvas>
      <div v-if="recordingStore.hasRecording" class="record-actions">
        <el-button :icon="'Refresh'" @click="recordingStore.clearRecording">重录</el-button>
        <el-button type="primary" :icon="'DataAnalysis'" @click="analyzeAndGoFeedback" :loading="recordingStore.isAnalyzing">
          {{ recordingStore.isAnalyzing ? '分析中...' : '分析发音' }}
        </el-button>
      </div>
    </div>

    <!-- 底部：常见误区 -->
    <div class="mistakes-section">
      <h3>常见误区</h3>
      <div class="mistake-list">
        <div class="mistake-item" v-if="unitId === 'ma'">
          <el-icon color="#e6a23c"><Warning /></el-icon>
          <div><strong>声调不够高平</strong><p>保持声带张力稳定，不要在结尾下掉。</p></div>
        </div>
        <div class="mistake-item" v-if="unitId === 'ba'">
          <el-icon color="#e6a23c"><Warning /></el-icon>
          <div><strong>送气与不送气混淆</strong><p>b是不送气音，p是送气音。把手放在嘴前感受气流。</p></div>
        </div>
        <div class="mistake-item">
          <el-icon color="#409eff"><InfoFilled /></el-icon>
          <div><strong>练习建议</strong><p>先听示范3-5次，再尝试录音。录完后对比分析结果。</p></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.learning-view { display: flex; flex-direction: column; gap: 20px; }
.teaching-section { background: white; border-radius: 12px; padding: 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.unit-info { flex: 1; }
.unit-character { font-size: 72px; font-weight: 700; color: #303133; line-height: 1; }
.unit-pinyin { font-size: 28px; color: #409eff; margin: 8px 0; }
.unit-desc { font-size: 14px; color: #909399; }
.unit-detail { font-size: 14px; color: #606266; margin-top: 8px; line-height: 1.6; }
.teaching-actions { display: flex; flex-direction: column; gap: 8px; }
.recording-section { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); text-align: center; }
.recording-section h3 { margin: 0 0 16px; font-size: 16px; color: #303133; }
.recording-controls { display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 16px; }
.record-btn { width: 64px; height: 64px; font-size: 24px; }
.record-btn.recording { animation: pulse 1s infinite; }
@keyframes pulse { 0%{transform:scale(1)} 50%{transform:scale(1.1)} 100%{transform:scale(1)} }
.record-time { font-size: 24px; font-weight: 600; color: #303133; font-variant-numeric: tabular-nums; }
.waveform-canvas { width: 100%; height: 120px; border-radius: 8px; background: #1a1a2e; }
.record-actions { margin-top: 16px; display: flex; justify-content: center; gap: 12px; }
.mistakes-section { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.mistakes-section h3 { margin: 0 0 16px; font-size: 16px; color: #303133; }
.mistake-list { display: flex; flex-direction: column; gap: 12px; }
.mistake-item { display: flex; gap: 12px; align-items: flex-start; padding: 12px; background: #f5f7fa; border-radius: 8px; }
.mistake-item strong { color: #303133; }
.mistake-item p { margin: 4px 0 0; color: #606266; font-size: 13px; }
</style>