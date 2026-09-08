<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUnitsStore } from '@/stores/units'
import { useUserStore } from '@/stores/user'
import { feedbackApi } from '@/api'
import { PLACE_FILTERS, METHOD_FILTERS, TAG_FILTERS } from '@/data/unitSearchMeta'
import PageFeedback from '@/components/PageFeedback.vue'
import SiteFooter from '@/components/SiteFooter.vue'

const route = useRoute()
const router = useRouter()
const unitsStore = useUnitsStore()
const userStore = useUserStore()

const requestText = ref('')
const submitting = ref(false)
const filterCategory = ref('all')
const filterPlace = ref('')
const filterMethod = ref('')
const filterTag = ref('')

const q = computed(() => String(route.query.q || ''))
const results = computed(() =>
  unitsStore.search(q.value, {
    category: filterCategory.value,
    place: filterPlace.value,
    method: filterMethod.value,
    tag: filterTag.value,
  })
)
const similar = computed(() => unitsStore.findSimilar(q.value, 4))

onMounted(async () => {
  if (!unitsStore.coreUnits.length) await unitsStore.fetchPublished()
})

async function submitRequest() {
  const text = requestText.value.trim() || q.value
  if (!text) {
    ElMessage.warning('请描述希望增加的音、字或问题')
    return
  }
  submitting.value = true
  try {
    await feedbackApi.submit({
      userId: userStore.userId,
      type: 'request',
      page: 'search',
      message: text,
    })
    ElMessage.success('已提交需求，感谢反馈')
    requestText.value = ''
  } catch {
    ElMessage.error('提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="search-view">
    <h2>搜索结果</h2>
    <p v-if="q" class="query">关键词：{{ q }}</p>
    <p class="hint">支持汉字、拼音、IPA、声母/韵母、发音部位、发音方法与常见问题标签。</p>

    <div class="filters">
      <el-select v-model="filterCategory" placeholder="类型" style="width: 120px">
        <el-option label="全部类型" value="all" />
        <el-option label="声母" value="声母" />
        <el-option label="韵母" value="韵母" />
        <el-option label="声调" value="声调" />
      </el-select>
      <el-select v-model="filterPlace" placeholder="发音部位" clearable style="width: 130px">
        <el-option v-for="p in PLACE_FILTERS" :key="p" :label="p" :value="p" />
      </el-select>
      <el-select v-model="filterMethod" placeholder="发音方法" clearable style="width: 130px">
        <el-option v-for="m in METHOD_FILTERS" :key="m" :label="m" :value="m" />
      </el-select>
      <el-select v-model="filterTag" placeholder="问题标签" clearable style="width: 140px">
        <el-option v-for="t in TAG_FILTERS" :key="t" :label="t" :value="t" />
      </el-select>
    </div>

    <div v-if="results.length" class="result-list">
      <el-card v-for="u in results" :key="u.id" shadow="hover" class="result-card">
        <div class="head">
          <strong>{{ u.character }}</strong>
          <span>{{ u.pinyin }}</span>
          <el-tag size="small">{{ u.category }}</el-tag>
          <el-tag v-if="unitsStore.getMeta(u.id)?.ipa" size="small" type="info">{{ unitsStore.getMeta(u.id)?.ipa }}</el-tag>
        </div>
        <p>{{ u.conclusion || u.description }}</p>
        <el-button type="primary" size="small" @click="router.push(`/learn/${u.id}`)">进入学习</el-button>
      </el-card>
    </div>

    <div v-else class="empty">
      <p>没有找到完全匹配的内容。</p>
      <h3>相近内容</h3>
      <div class="result-list">
        <el-card v-for="u in similar" :key="u.id" shadow="hover" class="result-card">
          <div class="head"><strong>{{ u.character }}</strong><span>{{ u.pinyin }}</span></div>
          <p>{{ u.conclusion }}</p>
          <el-button size="small" @click="router.push(`/learn/${u.id}`)">进入学习</el-button>
        </el-card>
      </div>
      <el-button @click="router.push('/map')">返回发音地图</el-button>
      <div class="request-box">
        <h3>希望增加此内容</h3>
        <el-input v-model="requestText" :placeholder="q ? `例如：希望增加「${q}」相关单元` : '描述希望增加的音、字或问题'" />
        <el-button type="primary" :loading="submitting" @click="submitRequest">提交需求</el-button>
      </div>
    </div>

    <PageFeedback page="search" type="request" />
    <SiteFooter />
  </div>
</template>

<style scoped>
.search-view { max-width: 800px; margin: 0 auto; }
.query, .hint { color: #909399; font-size: 13px; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 16px; }
.result-list { display: flex; flex-direction: column; gap: 12px; margin: 16px 0; }
.result-card .head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.result-card p { color: #606266; font-size: 14px; margin: 0 0 12px; }
.empty { padding: 16px; background: #fff; border-radius: 12px; }
.request-box { margin-top: 20px; display: flex; flex-direction: column; gap: 8px; }
@media (max-width: 600px) { .filters .el-select { width: 100% !important; } }
</style>
