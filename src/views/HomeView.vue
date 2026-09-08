<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUnitsStore } from '@/stores/units'
import { FAQ_ITEMS, HOME_ACTIONS } from '@/data/coreUnits'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()
const unitsStore = useUnitsStore()
const searchQuery = ref('')

onMounted(() => unitsStore.fetchPublished())

function doSearch() {
  router.push({ path: '/search', query: { q: searchQuery.value } })
}

function goAction(action: typeof HOME_ACTIONS[number]) {
  router.push(action.route)
}

function goFaq(item: typeof FAQ_ITEMS[number]) {
  router.push({ path: '/search', query: { q: item.keyword } })
}
</script>

<template>
  <div class="home-view">
    <section class="hero">
      <h1>看得见的声音</h1>
      <p class="tagline">搜一个音、看懂发音、跟着练、录音比较</p>
      <el-input
        v-model="searchQuery"
        size="large"
        placeholder="输入汉字、拼音或你的发音问题"
        prefix-icon="Search"
        clearable
        @keyup.enter="doSearch"
      >
        <template #append>
          <el-button type="primary" @click="doSearch">搜索</el-button>
        </template>
      </el-input>
    </section>

    <section class="actions">
      <el-button
        v-for="a in HOME_ACTIONS"
        :key="a.label"
        size="large"
        class="action-btn"
        @click="goAction(a)"
      >
        <strong>{{ a.label }}</strong>
        <span>{{ a.desc }}</span>
      </el-button>
    </section>

    <section class="faq">
      <h2>常见问题</h2>
      <div class="faq-list">
        <el-card v-for="f in FAQ_ITEMS" :key="f.q" shadow="hover" class="faq-card" @click="goFaq(f)">
          {{ f.q }}
        </el-card>
      </div>
    </section>

    <section class="units">
      <h2>首批学习单元（12个）</h2>
      <p class="hint">仅展示已完成并发布的单元，不含空卡片或「敬请期待」。</p>
      <div class="unit-grid" v-loading="unitsStore.loading">
        <el-card
          v-for="u in unitsStore.coreUnits"
          :key="u.id"
          shadow="hover"
          class="unit-card"
          @click="router.push(`/learn/${u.id}`)"
        >
          <div class="char">{{ u.character }}</div>
          <div class="py">{{ u.pinyin }}</div>
          <p>{{ u.conclusion || u.description }}</p>
        </el-card>
      </div>
    </section>

    <section class="quick-test">
      <el-card shadow="never">
        <h2>快速体验</h2>
        <p>朗读「妈」字，约 30 秒，体验录音质量检查与声调分析。</p>
        <p class="meta">用途：临时体验检测流程；同意保存后才进入个人档案。</p>
        <el-button type="primary" size="large" @click="router.push('/test?unit=ma')">开始体验</el-button>
      </el-card>
    </section>

    <section class="profile-entry">
      <el-button text type="primary" @click="router.push('/archive')">进入我的声音档案 →</el-button>
      <span class="guest-hint">未登录也可临时体验；保存记录需先同意隐私说明。</span>
    </section>

    <SiteFooter />
  </div>
</template>

<style scoped>
.home-view { max-width: 960px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px; }
.hero { background: #fff; border-radius: 12px; padding: 32px 24px; }
.hero h1 { margin: 0 0 8px; font-size: 28px; color: #303133; }
.tagline { margin: 0 0 20px; color: #606266; }
.actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.action-btn { height: auto; padding: 16px; display: flex; flex-direction: column; align-items: flex-start; text-align: left; white-space: normal; }
.action-btn strong { font-size: 16px; margin-bottom: 4px; }
.action-btn span { font-size: 12px; color: #909399; font-weight: normal; }
.faq h2, .units h2 { margin: 0 0 12px; font-size: 18px; }
.faq-list { display: grid; gap: 10px; }
.faq-card { cursor: pointer; }
.hint { color: #909399; font-size: 13px; margin: 0 0 12px; }
.unit-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.unit-card { cursor: pointer; text-align: center; }
.char { font-size: 36px; font-weight: 700; }
.py { color: #409eff; margin-bottom: 8px; }
.unit-card p { font-size: 12px; color: #909399; margin: 0; line-height: 1.4; }
.quick-test h2 { margin: 0 0 8px; font-size: 18px; }
.quick-test p { margin: 0 0 8px; color: #606266; }
.meta { font-size: 12px; color: #909399; }
.profile-entry { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.guest-hint { font-size: 13px; color: #909399; }
</style>
