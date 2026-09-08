<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useRecordingStore } from '@/stores/recording'
import { useUnitsStore } from '@/stores/units'
import { useUserStore } from '@/stores/user'
import { useArchiveConsent } from '@/composables/useArchiveConsent'
import { useSpeechDemo } from '@/composables/useSpeechDemo'
import { CORE_UNIT_IDS } from '@/data/coreUnits'
import PageFeedback from '@/components/PageFeedback.vue'

const route = useRoute()
const router = useRouter()
const recordingStore = useRecordingStore()
const unitsStore = useUnitsStore()
const userStore = useUserStore()
const { consented } = useArchiveConsent()
const speech = useSpeechDemo()

const unitId = ref(String(route.query.unit || 'ma'))
const envOk = ref(false)
const authOk = ref(false)
const countdown = ref(0)
const unit = ref<any>(null)

const verifiedTasks = computed(() =>
  unitsStore.coreUnits.filter(u => u.verified && CORE_UNIT_IDS.includes(u.id as any))
)

onMounted(async () => {
  await unitsStore.fetchPublished()
  unit.value = await unitsStore.getUnit(unitId.value)
})

async function selectTask(id: string) {
  unitId.value = id
  unit.value = await unitsStore.getUnit(id)
  recordingStore.clearRecording()
  router.replace({ query: { unit: id } })
}

async function checkMic() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    authOk.value = true
    stream.getTracks().forEach(t => t.stop())
  } catch {
    ElMessage.error('麦克风未授权。请在浏览器地址栏允许麦克风后重试。')
  }
}

async function startTest() {
  if (!envOk.value || !authOk.value) {
    ElMessage.warning('请先确认环境安静并完成麦克风授权')
    return
  }
  countdown.value = 3
  const timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
      recordingStore.startRecording()
    }
  }, 1000)
}

async function submit() {
  recordingStore.stopRecording()
  await recordingStore.analyzeRecording(unitId.value)
  if (recordingStore.error) {
    ElMessage.error(recordingStore.error)
    return
  }
  const a = recordingStore.assessment
  if (consented.value && a?.evaluable) {
    try {
      await userStore.addLearningRecord({
        unitId: unitId.value,
        pinyin: unit.value?.pinyin || '',
        character: unit.value?.character || '',
        score: a.score,
        accuracy: a.accuracy,
        fluency: a.fluency,
        pronunciation: a.pronunciation,
        duration: recordingStore.duration,
        feedback: a.feedback.map(f => f.phenomenon).join('; '),
        audioBlob: recordingStore.recordingState.audioBlob ?? new Blob(),
      })
    } catch { /* 不阻塞 */ }
  }
  router.push(`/feedback/${unitId.value}`)
}
</script>

<template>
  <div class="test-center">
    <h2>检测中心</h2>
    <p class="intro">仅开放已通过验证的检测任务；首页、单元页与检测中心进入同一任务时，结果口径一致。</p>

    <!-- TEST-01 任务选择 -->
    <el-card class="step-card">
      <h4>1. 选择任务</h4>
      <el-radio-group v-model="unitId" @change="selectTask">
        <el-radio v-for="t in verifiedTasks" :key="t.id" :value="t.id" border class="task-radio">
          {{ t.character }}（{{ t.pinyin }}）
        </el-radio>
      </el-radio-group>
    </el-card>

    <el-card v-if="unit" class="task-card">
      <h3>任务：{{ unit.character }}（{{ unit.pinyin }}）</h3>
      <p>{{ unit.conclusion }}</p>
      <p class="meta">请朗读：{{ unit.character.split('/')[0] }} · 预计约 30 秒</p>
    </el-card>

    <!-- TEST-02 示范 -->
    <el-card class="step-card">
      <h4>2. 听示范</h4>
      <el-button @click="speech.speak(unit?.character?.split('/')[0] || '妈', 'normal')">正常速度</el-button>
      <el-button @click="speech.speak(unit?.character?.split('/')[0] || '妈', 'slow')">慢速</el-button>
      <p class="tts-note">{{ speech.disclaimer }}</p>
    </el-card>

    <!-- TEST-03 环境检查 -->
    <el-card class="step-card">
      <h4>3. 环境检查</h4>
      <el-checkbox v-model="envOk">我已确认环境安静、麦克风距离约 10–20 cm、设备正常</el-checkbox>
    </el-card>

    <!-- TEST-04/05 用途与授权 -->
    <el-card class="step-card">
      <h4>4. 用途说明与麦克风授权</h4>
      <p>录音用于本次检测分析。{{ consented ? '已同意保存到个人档案。' : '未同意前不会长期保存，也不用于研究或模型训练。' }}</p>
      <el-button @click="checkMic">请求麦克风权限</el-button>
      <el-tag v-if="authOk" type="success" style="margin-left:8px">已授权</el-tag>
      <p v-else class="hint">若拒绝授权，请在浏览器设置中开启麦克风后刷新页面。</p>
    </el-card>

    <!-- TEST-06 录音 -->
    <el-card class="step-card">
      <h4>5. 录音</h4>
      <div v-if="countdown > 0" class="countdown">{{ countdown }}</div>
      <el-button v-if="!recordingStore.isRecording" type="danger" @click="startTest">开始录音</el-button>
      <el-button v-else type="info" @click="recordingStore.stopRecording()">停止</el-button>
      <audio v-if="recordingStore.audioUrl" :src="recordingStore.audioUrl" controls class="playback" />
      <div class="actions">
        <el-button @click="recordingStore.clearRecording()">重录</el-button>
        <el-button type="primary" :disabled="!recordingStore.hasRecording" :loading="recordingStore.isAnalyzing" @click="submit">提交分析</el-button>
      </div>
    </el-card>

    <!-- TEST-07 处理状态 -->
    <el-alert
      v-if="recordingStore.isAnalyzing"
      type="info"
      title="正在检查与分析录音…"
      description="包含录音质量检测与发音分析，请稍候。"
      show-icon
      :closable="false"
    />
    <el-alert
      v-if="recordingStore.error"
      type="error"
      :title="recordingStore.error"
      description="请检查后端服务是否启动、麦克风是否正常，然后重录。"
      show-icon
    />

    <PageFeedback page="test-center" :unit-id="unitId" type="result" />
  </div>
</template>

<style scoped>
.test-center { max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.intro { color: #606266; font-size: 14px; margin: 0; }
.task-card h3 { margin: 0 0 8px; }
.meta, .tts-note, .hint { font-size: 13px; color: #909399; }
.step-card h4 { margin: 0 0 12px; }
.task-radio { margin: 4px 8px 4px 0; }
.countdown { font-size: 48px; font-weight: 700; text-align: center; color: #409eff; }
.playback { display: block; margin-top: 12px; width: 100%; }
.actions { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
</style>
