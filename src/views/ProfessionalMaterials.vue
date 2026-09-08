<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { PRO_CATEGORIES, PRO_MATERIALS } from '@/data/proMaterials'
import PageFeedback from '@/components/PageFeedback.vue'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()
const category = ref('')

const filtered = () => category.value
  ? PRO_MATERIALS.filter(m => m.category === category.value)
  : PRO_MATERIALS
</script>

<template>
  <div class="materials-view">
    <h2>专业资料</h2>
    <p class="intro">按需查看术语与证据入口；只提供摘要与合法引用，不复制未授权全文。</p>

    <div class="cats">
      <el-tag :effect="!category ? 'dark' : 'plain'" @click="category = ''" style="cursor:pointer">全部</el-tag>
      <el-tag
        v-for="c in PRO_CATEGORIES"
        :key="c.id"
        :effect="category === c.id ? 'dark' : 'plain'"
        style="cursor:pointer;margin-left:8px"
        @click="category = c.id"
      >{{ c.name }}</el-tag>
    </div>

    <div class="list">
      <el-card v-for="m in filtered()" :key="m.id" shadow="hover">
        <h3>{{ m.title }}</h3>
        <p>{{ m.summary }}</p>
        <p class="scope"><strong>适用边界：</strong>{{ m.scope }}</p>
        <p class="meta">来源：{{ m.source }} · 许可：{{ m.license }}</p>
        <div class="related">
          <span>相关单元：</span>
          <el-button v-for="uid in m.relatedUnits" :key="uid" link type="primary" @click="router.push(`/learn/${uid}`)">{{ uid }}</el-button>
        </div>
      </el-card>
    </div>

    <PageFeedback page="materials" type="content" />
    <SiteFooter />
  </div>
</template>

<style scoped>
.materials-view { max-width: 900px; margin: 0 auto; }
.intro { color: #606266; margin-bottom: 16px; }
.cats { margin-bottom: 16px; }
.list { display: flex; flex-direction: column; gap: 12px; }
.scope, .meta { font-size: 13px; color: #909399; }
.related { margin-top: 8px; }
</style>
