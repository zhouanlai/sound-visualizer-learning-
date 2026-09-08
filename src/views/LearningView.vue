<script setup lang="ts">
import { ref, onUnmounted, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useRecordingStore } from '@/stores/recording'
import { useUserStore } from '@/stores/user'
import { useUnitsStore } from '@/stores/units'
import { useArchiveConsent } from '@/composables/useArchiveConsent'
import { useSpeechDemo } from '@/composables/useSpeechDemo'
import PageFeedback from '@/components/PageFeedback.vue'
import { UNIT_SEARCH_META } from '@/data/unitSearchMeta'
import type { PublishedUnit } from '@/data/coreUnits'

const route = useRoute()
const router = useRouter()
const recordingStore = useRecordingStore()
const userStore = useUserStore()
const unitsStore = useUnitsStore()
const { consented } = useArchiveConsent()
const speech = useSpeechDemo()
const playingNormal = computed(() => speech.isPlaying.value && speech.mode.value === 'normal')
const playingSlow = computed(() => speech.isPlaying.value && speech.mode.value === 'slow')

const unitId = computed(() => route.params.id as string)
const unit = ref<PublishedUnit | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
let animationFrame: number | null = null

const isVerified = computed(() => !!unit.value?.verified)
const unitMeta = computed(() => (unitId.value ? UNIT_SEARCH_META[unitId.value] : undefined))
const practiceSteps = computed(() => {
  const steps = unit.value?.steps || []
  if (steps.length) return steps
  return [
    { title: '听示范', text: '先听 3 遍正常与慢速示范，注意口型与声调走向。' },
    { title: '跟读', text: '不录音，先跟读 5 遍，感受发音部位。' },
    { title: '录音', text: '按下录音键，清晰朗读目标音节。' },
    { title: '看结果', text: '提交后查看现象、可能环节与短练习建议。' },
    { title: '再录', text: '按建议调整后重录，比较前后差异。' },
  ]
})

onMounted(async () => {
  unit.value = await unitsStore.getUnit(unitId.value)
})

watch(unitId, async (id) => {
  unit.value = await unitsStore.getUnit(id)
})

async function playDemo(speed: 'normal' | 'slow') {
  if (!unit.value) return
  try {
    await speech.speak(unit.value.character, speed)
  } catch {
    ElMessage.error('播放失败')
  }
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
    ctx!.lineWidth = 2
    ctx!.strokeStyle = '#409eff'
    ctx!.beginPath()
    const sw = canvas.width / bufLen
    let x = 0
    for (let i = 0; i < bufLen; i++) {
      const y = ((data[i] ?? 128) / 128.0) * canvas.height / 2
      i === 0 ? ctx!.moveTo(x, y) : ctx!.lineTo(x, y)
      x += sw
    }
    ctx!.stroke()
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
  if (consented.value && assessment?.evaluable) {
    try {
      await userStore.addLearningRecord({
        unitId: unitId.value,
        pinyin: unit.value?.pinyin || '',
        character: unit.value?.character || '',
        score: assessment.score,
        accuracy: assessment.accuracy,
        fluency: assessment.fluency,
        pronunciation: assessment.pronunciation,
        duration: recordingStore.duration,
        feedback: assessment.feedback.map(f => f.phenomenon).join('; '),
        audioBlob: recordingStore.recordingState.audioBlob ?? new Blob(),
      })
    } catch {
      ElMessage.warning('未保存到档案（需同意保存或后端未启动）')
    }
  }
  router.push(`/feedback/${unitId.value}`)
}

onUnmounted(() => stopVisualization())
</script>

<template>
  <div class="learning-view" v-if="unit">
    <section class="conclusion card">
      <p class="label">一句话结论</p>
      <h2>{{ unit.conclusion }}</h2>
    </section>

    <section class="card grid-2">
      <div>
        <div class="char">{{ unit.character }}</div>
        <div class="py">{{ unit.pinyin }}</div>
        <p>{{ unit.detail }}</p>
        <div class="articulation">
          <strong>看得见的构形（示意）</strong>
          <p>关注唇形、舌位与下颌开合。详细 3D 剖面见检测结果页。</p>
        </div>
      </div>
      <div class="demo">
        <strong>听得见的声音</strong>
        <div class="demo-btns">
          <el-button type="primary" :loading="playingNormal" @click="playDemo('normal')">正常示范</el-button>
          <el-button :loading="playingSlow" @click="playDemo('slow')">慢速示范</el-button>
        </div>
        <p class="tts-note">{{ speech.disclaimer }}</p>
        <p class="ipa">代表材料：拼音 {{ unit.pinyin }} · IPA {{ unitMeta?.ipa || '—' }} · 类别 {{ unit.category }}</p>
        <el-collapse v-if="unitMeta?.professional?.length" class="pro-block">
          <el-collapse-item title="专业资料（按需展开）" name="pro">
            <ul>
              <li v-for="t in unitMeta.professional" :key="t.term"><strong>{{ t.term }}</strong>：{{ t.explain }}</li>
            </ul>
            <el-button link type="primary" @click="router.push('/materials')">查看更多专业资料</el-button>
            <p class="boundary">资料仅用于理解发音，不构成医学诊断依据。</p>
          </el-collapse-item>
        </el-collapse>
      </div>
    </section>

    <section class="card">
      <h3>跟着练（{{ practiceSteps.length }} 步）</h3>
      <ol>
        <li v-for="(s, i) in practiceSteps" :key="i">
          <strong>{{ s.title || `步骤 ${i + 1}` }}</strong> — {{ s.text || s }}
        </li>
      </ol>
    </section>

    <section class="card" v-if="unit.mistakes?.length">
      <h3>常见误区</h3>
      <div v-for="(m, i) in unit.mistakes" :key="i" class="mistake">{{ m.title || m.phenomenon }}：{{ m.text || m.hint }}</div>
    </section>

    <section class="card record" v-if="isVerified">
      <h3>录音比较</h3>
      <p>该任务已通过验证，可提交 AI 检测。</p>
      <div class="record-row">
        <el-button v-if="!recordingStore.isRecording" type="danger" circle size="large" @click="startRecording" />
        <el-button v-else type="info" circle size="large" @click="stopRecording" />
        <span>{{ recordingStore.formattedDuration }}</span>
      </div>
      <canvas ref="canvasRef" width="600" height="100" class="wave" />
      <div v-if="recordingStore.hasRecording" class="record-actions">
        <el-button @click="recordingStore.clearRecording">重录</el-button>
        <el-button type="primary" :loading="recordingStore.isAnalyzing" @click="analyzeAndGoFeedback">提交分析</el-button>
      </div>
      <p v-if="!consented" class="consent-hint">未同意保存时，录音仅用于本次分析，不会写入档案。</p>
    </section>
    <section class="card" v-else>
      <el-alert type="info" title="该单元检测尚未开放" description="可先学习跟读；开放检测的核心单元请从发音库进入。" show-icon :closable="false" />
    </section>

    <section class="card" v-if="unit.related?.length">
      <h3>相关学习</h3>
      <el-button v-for="rid in unit.related" :key="rid" link type="primary" @click="router.push(`/learn/${rid}`)">
        {{ unitsStore.unitLabel(rid) }}
      </el-button>
    </section>

    <PageFeedback :page="`learn/${unitId}`" :unit-id="unitId" type="learning" />
  </div>
  <el-empty v-else description="单元加载中或不存在" />
</template>

<style scoped>
.learning-view { display: flex; flex-direction: column; gap: 16px; max-width: 900px; margin: 0 auto; }
.card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.conclusion .label { font-size: 13px; color: #909399; margin: 0; }
.conclusion h2 { margin: 8px 0 0; font-size: 20px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.char { font-size: 64px; font-weight: 700; }
.py { font-size: 24px; color: #409eff; margin-bottom: 8px; }
.demo-btns { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0; }
.tts-note, .consent-hint, .ipa, .boundary { font-size: 12px; color: #909399; }
.pro-block { margin-top: 12px; }
.record-row { display: flex; align-items: center; gap: 12px; margin: 12px 0; }
.wave { width: 100%; border-radius: 8px; background: #1a1a2e; }
.record-actions { display: flex; gap: 8px; margin-top: 12px; }
.mistake { padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 14px; }
@media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
