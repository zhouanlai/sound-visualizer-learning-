<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { PINYIN_UNITS, TONE_UNITS } from '@/data/pinyinUnits'

const router = useRouter()
const searchQuery = ref('')

interface PronunciationUnit {
  id: string
  pinyin: string
  character: string
  pinyinTone: string
  description: string
  category: 'initial' | 'final' | 'tone'
  color: string
  progress: number
}

// 手工精选单元（保留演示进度数据）
const featuredUnits: PronunciationUnit[] = [
  { id: 'ma', pinyin: 'ma', character: '妈', pinyinTone: 'mā', description: '双唇音+开口呼', category: 'initial', color: '#409eff', progress: 85 },
  { id: 'ba', pinyin: 'ba', character: '八', pinyinTone: 'bā', description: '双唇音+开口呼', category: 'initial', color: '#409eff', progress: 72 },
  { id: 'pa', pinyin: 'pa', character: '趴', pinyinTone: 'pā', description: '双唇音+开口呼', category: 'initial', color: '#409eff', progress: 0 },
  { id: 'ta', pinyin: 'ta', character: '他', pinyinTone: 'tā', description: '舌尖中音+开口呼', category: 'initial', color: '#409eff', progress: 0 },
  { id: 'yi', pinyin: 'yi', character: '一', pinyinTone: 'yī', description: '齐齿呼', category: 'final', color: '#67c23a', progress: 0 },
  { id: 'wu', pinyin: 'wu', character: '五', pinyinTone: 'wǔ', description: '合口呼', category: 'final', color: '#67c23a', progress: 0 },
  { id: 'yu', pinyin: 'yu', character: '鱼', pinyinTone: 'yú', description: '撮口呼', category: 'final', color: '#67c23a', progress: 0 },
  { id: 'mao', pinyin: 'mao', character: '猫', pinyinTone: 'māo', description: '双唇音+复韵母', category: 'initial', color: '#409eff', progress: 0 },
  { id: 'gou', pinyin: 'gou', character: '狗', pinyinTone: 'gǒu', description: '舌根音+复韵母', category: 'initial', color: '#409eff', progress: 0 },
  { id: 'niao', pinyin: 'niao', character: '鸟', pinyinTone: 'niǎo', description: '舌尖中音+复韵母', category: 'initial', color: '#409eff', progress: 0 },
  { id: 'ma_t2', pinyin: 'ma', character: '麻', pinyinTone: 'má', description: '第二声练习', category: 'tone', color: '#e6a23c', progress: 0 },
  { id: 'ma_t3', pinyin: 'ma', character: '马', pinyinTone: 'mǎ', description: '第三声练习', category: 'tone', color: '#e6a23c', progress: 0 },
]

// 声母发音部位说明
const initialDescMap: Record<string, string> = {
  b: '双唇音', p: '双唇音', m: '双唇鼻音', f: '唇齿音',
  d: '舌尖中音', t: '舌尖中音', n: '舌尖中鼻音', l: '舌尖中边音',
  g: '舌根音', k: '舌根音', h: '舌根音',
  j: '舌面音', q: '舌面音', x: '舌面音',
  zh: '翘舌音', ch: '翘舌音', sh: '翘舌音', r: '翘舌音',
  z: '平舌音', c: '平舌音', s: '平舌音',
}

// 判断韵母类型（单韵母/复韵母/鼻韵母）
function finalKind(pinyin: string): string {
  if (/(?:ng|n)$/.test(pinyin) || /iong|iang|uang|uan|ian|uan|uen|ün|uan/.test(pinyin)) return '鼻韵母'
  if (pinyin.length > 1) return '复韵母'
  return '单韵母'
}

// 从共享数据生成全量发音单元（声母 + 韵母）
function buildPinyinUnits(): PronunciationUnit[] {
  const list: PronunciationUnit[] = []
  for (const [id, meta] of Object.entries(PINYIN_UNITS)) {
    // 零声母音节（y/w 开头）归为韵母类
    const initialMatch = id.match(/^(zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])/)
    const initial = (initialMatch && initialMatch[1]) || ''
    const isFinal = initial === 'y' || initial === 'w'
    const desc = isFinal
      ? `零声母+${finalKind(id.replace(/^[yw]/, ''))}`
      : `${initialDescMap[initial] || '声母'}+${finalKind(id.replace(new RegExp(`^${initial}`), ''))}`
    list.push({
      id,
      pinyin: id,
      character: meta.char,
      pinyinTone: meta.tone,
      description: desc,
      category: isFinal ? 'final' : 'initial',
      color: isFinal ? '#67c23a' : '#409eff',
      progress: 0,
    })
  }
  return list
}

// 声调练习单元
function buildToneUnits(): PronunciationUnit[] {
  return Object.entries(TONE_UNITS).map(([id, meta]) => ({
    id,
    pinyin: id.replace(/_\w+$/, ''),
    character: meta.char,
    pinyinTone: meta.tone,
    description: '声调练习',
    category: 'tone' as const,
    color: '#e6a23c',
    progress: 0,
  }))
}

// 合并：手工精选（含进度）+ 自动生成全量（去重，手工优先）
const units: PronunciationUnit[] = [
  ...featuredUnits,
  ...buildPinyinUnits(),
  ...buildToneUnits(),
].filter((u, idx, arr) => arr.findIndex(x => x.id === u.id) === idx)

// 分类标签计数
const counts = computed(() => ({
  all: units.length,
  initial: units.filter(u => u.category === 'initial').length,
  final: units.filter(u => u.category === 'final').length,
  tone: units.filter(u => u.category === 'tone').length,
}))

const filteredUnits = computed(() => {
  if (!searchQuery.value) return units
  const q = searchQuery.value.toLowerCase()
  return units.filter(u =>
    u.pinyin.includes(q) ||
    u.character.includes(q) ||
    u.pinyinTone.includes(q)
  )
})

const categoryLabel = (cat: string) => {
  const map: Record<string, string> = { initial: '声母', final: '韵母', tone: '声调' }
  return map[cat] || cat
}

const handleLearn = (unit: PronunciationUnit) => {
  router.push(`/learn/${unit.id}`)
}

const getProgressColor = (progress: number) => {
  if (progress >= 80) return '#67c23a'
  if (progress >= 60) return '#e6a23c'
  return '#409eff'
}
</script>

<template>
  <div class="pronunciation-library">
    <div class="library-header">
      <div>
        <h3>发音库</h3>
        <p>共 {{ units.length }} 个发音单元，点击卡片开始学习</p>
      </div>
      <el-input
        v-model="searchQuery"
        placeholder="搜索拼音或汉字..."
        prefix-icon="Search"
        style="width: 280px"
        clearable
      />
    </div>

    <!-- 分类筛选 -->
    <div class="category-filter">
      <el-tag :type="'primary'" effect="plain">全部 ({{ counts.all }})</el-tag>
      <el-tag effect="plain">声母 ({{ counts.initial }})</el-tag>
      <el-tag effect="plain" type="success">韵母 ({{ counts.final }})</el-tag>
      <el-tag effect="plain" type="warning">声调 ({{ counts.tone }})</el-tag>
    </div>

    <!-- 卡片网格 -->
    <div class="unit-grid">
      <el-card
        v-for="unit in filteredUnits"
        :key="unit.id"
        class="unit-card"
        :class="{ completed: unit.progress >= 80, 'in-progress': unit.progress > 0 && unit.progress < 80 }"
        shadow="hover"
        @click="handleLearn(unit)"
      >
        <div class="card-content">
          <div class="unit-number">#{{ units.indexOf(unit) + 1 }}</div>
          <div class="unit-character">{{ unit.character }}</div>
          <div class="unit-pinyin">{{ unit.pinyinTone }}</div>
          <div class="unit-desc">{{ unit.description }}</div>

          <el-progress
            :percentage="unit.progress"
            :color="getProgressColor(unit.progress)"
            :stroke-width="6"
            class="unit-progress"
          />

          <div class="unit-status">
            <el-tag v-if="unit.progress >= 80" type="success" size="small">已完成</el-tag>
            <el-tag v-else-if="unit.progress > 0" type="warning" size="small">学习中</el-tag>
            <el-tag v-else type="info" size="small">未开始</el-tag>
          </div>
        </div>

        <div class="card-action">
          <el-button type="primary" size="small" :icon="'Microphone'">
            {{ unit.progress > 0 ? '继续学习' : '开始学习' }}
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.pronunciation-library {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.library-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.library-header h3 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.library-header p {
  margin: 8px 0 0;
  color: #909399;
  font-size: 14px;
}

.category-filter {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.unit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.unit-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 12px;
  overflow: hidden;
}

.unit-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.unit-card.completed {
  border-left: 4px solid #67c23a;
}

.unit-card.in-progress {
  border-left: 4px solid #e6a23c;
}

.card-content {
  text-align: center;
  padding: 8px 0;
}

.unit-number {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.unit-character {
  font-size: 48px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
  margin-bottom: 8px;
}

.unit-pinyin {
  font-size: 20px;
  color: #409eff;
  font-weight: 500;
  margin-bottom: 4px;
}

.unit-desc {
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
}

.unit-progress {
  margin: 8px 0;
}

.unit-status {
  margin-top: 8px;
}

.card-action {
  margin-top: 12px;
  text-align: center;
}
</style>