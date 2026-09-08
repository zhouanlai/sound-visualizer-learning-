<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { learningRecordApi } from '@/api'
import { useArchiveConsent } from '@/composables/useArchiveConsent'
import PageFeedback from '@/components/PageFeedback.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import type { LearningRecord } from '@/types'

const router = useRouter()
const userStore = useUserStore()
const { consented, grant, revoke } = useArchiveConsent()

const compareUnit = ref('')
const leftId = ref('')
const rightId = ref('')

onMounted(async () => {
  if (consented.value) await userStore.fetchLearningRecords()
})

const byUnit = computed(() => {
  const map = new Map<string, LearningRecord[]>()
  for (const r of userStore.learningRecords) {
    if (!map.has(r.unitId)) map.set(r.unitId, [])
    map.get(r.unitId)!.push(r)
  }
  return map
})

const unitOptions = computed(() => [...byUnit.value.keys()])

const compareRecords = computed(() => {
  if (!compareUnit.value) return []
  return (byUnit.value.get(compareUnit.value) || []).slice(0, 10)
})

async function enableArchive() {
  grant()
  await userStore.fetchLearningRecords()
  ElMessage.success('已同意保存个人声音档案')
}

async function clearArchive() {
  await ElMessageBox.confirm('确定清空全部学习记录？此操作不可恢复。', '撤回同意并删除')
  await learningRecordApi.deleteAll(userStore.userId)
  revoke()
  userStore.learningRecords = []
  ElMessage.success('已清空档案')
}

async function deleteOne(id: string) {
  await learningRecordApi.delete(id)
  await userStore.fetchLearningRecords()
}

async function play(id: string) {
  const url = await learningRecordApi.getRecordAudio(id)
  new Audio(url).play().catch(() => {})
}

const leftRecord = computed(() => compareRecords.value.find(r => r.id === leftId.value))
const rightRecord = computed(() => compareRecords.value.find(r => r.id === rightId.value))
</script>

<template>
  <div class="archive-view">
    <h2>我的声音学习档案</h2>

    <el-card class="consent-card">
      <h3>保存与隐私</h3>
      <p>访客录音默认不长期保留。同意后才写入个人档案，可随时单条删除或全部清空。</p>
      <div class="consent-actions">
        <el-button v-if="!consented" type="primary" @click="enableArchive">同意保存到我的档案</el-button>
        <template v-else>
          <el-tag type="success">已同意保存</el-tag>
          <el-button type="danger" plain @click="clearArchive">撤回同意并全部删除</el-button>
        </template>
      </div>
    </el-card>

    <template v-if="consented">
      <div class="stats">
        <el-card>练习 {{ userStore.totalPracticeCount }} 次</el-card>
        <el-card>平均分 {{ userStore.averageScore }}</el-card>
      </div>

      <el-card class="compare-card">
        <h3>同任务比较</h3>
        <el-select v-model="compareUnit" placeholder="选择任务/单元" style="width:100%;margin-bottom:12px">
          <el-option v-for="u in unitOptions" :key="u" :label="u" :value="u" />
        </el-select>
        <div v-if="compareRecords.length >= 2" class="compare-pick">
          <el-select v-model="leftId" placeholder="较早一次">
            <el-option v-for="r in compareRecords" :key="r.id" :label="new Date(r.createdAt).toLocaleString()" :value="r.id" />
          </el-select>
          <el-select v-model="rightId" placeholder="较近一次">
            <el-option v-for="r in compareRecords" :key="r.id" :label="new Date(r.createdAt).toLocaleString()" :value="r.id" />
          </el-select>
        </div>
        <div v-if="leftRecord && rightRecord" class="compare-result">
          <div><strong>记录 A</strong> 评分 {{ leftRecord.score }} · 准确度 {{ leftRecord.accuracy }}%</div>
          <div><strong>记录 B</strong> 评分 {{ rightRecord.score }} · 准确度 {{ rightRecord.accuracy }}%</div>
          <p>变化提示：评分差 {{ rightRecord.score - leftRecord.score }} 分（仅供个人参考，不作排名）</p>
          <el-button size="small" @click="play(leftRecord.id)">播放 A</el-button>
          <el-button size="small" @click="play(rightRecord.id)">播放 B</el-button>
        </div>
        <p v-else-if="compareUnit" class="hint">该任务至少需要 2 条记录才可并排比较。</p>
      </el-card>

      <el-card>
        <template #header><span>时间线</span></template>
        <el-table :data="userStore.learningRecords" stripe empty-text="暂无记录">
          <el-table-column label="时间" width="170"><template #default="{ row }">{{ new Date(row.createdAt).toLocaleString() }}</template></el-table-column>
          <el-table-column prop="unitId" label="任务" width="100" />
          <el-table-column prop="character" label="汉字" width="70" />
          <el-table-column prop="score" label="评分" width="80" />
          <el-table-column prop="feedback" label="结论" show-overflow-tooltip />
          <el-table-column label="操作" width="220">
            <template #default="{ row }">
              <el-button size="small" @click="play(row.id)">播放</el-button>
              <el-button size="small" @click="router.push(`/learn/${row.unitId}`)">重练</el-button>
              <el-button size="small" type="danger" @click="deleteOne(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <PageFeedback page="archive" type="learning" />
    <SiteFooter />
  </div>
</template>

<style scoped>
.archive-view { max-width: 960px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.consent-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 12px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
.compare-pick { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.compare-result { font-size: 14px; line-height: 1.8; }
.hint { color: #909399; font-size: 13px; }
@media (max-width: 600px) { .compare-pick { grid-template-columns: 1fr; } }
</style>
