<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { PINYIN_UNITS } from '@/data/pinyinUnits'

const router = useRouter()
const searchQuery = ref('')

// 声母表
const initials = ['b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h', 'j', 'q', 'x', 'zh', 'ch', 'sh', 'r', 'z', 'c', 's', 'y', 'w']

// 韵母表
const finals = [
  'a', 'o', 'e', 'i', 'u', 'ü',
  'ai', 'ei', 'ao', 'ou',
  'an', 'en', 'ang', 'eng', 'ong',
  'ia', 'ie', 'iao', 'iou', 'ian', 'in', 'iang', 'ing', 'iong',
  'ua', 'uo', 'uai', 'uei', 'uan', 'uen', 'uang', 'ueng',
  'üe', 'üan', 'ün',
  'er'
]

// 声调
const tones = [
  { mark: 'ˉ', name: '第一声（阴平）', color: '#e74c3c' },
  { mark: 'ˊ', name: '第二声（阳平）', color: '#e67e22' },
  { mark: 'ˇ', name: '第三声（上声）', color: '#2ecc71' },
  { mark: 'ˋ', name: '第四声（去声）', color: '#3498db' },
]

// 可学习单元：由共享拼音数据派生（key = 声母+韵母，value = 代表汉字）
const availableUnits: Record<string, string> = Object.fromEntries(
  Object.entries(PINYIN_UNITS).map(([k, v]) => [k, v.char])
)

// 可学习单元总数（自动统计）
const availableCount = Object.keys(availableUnits).length

function isAvailable(initial: string, finalChar: string): boolean {
  return `${initial}${finalChar}` in availableUnits
}

function getCharacter(initial: string, finalChar: string): string {
  return availableUnits[`${initial}${finalChar}`] || ''
}

function handleClick(initial: string, finalChar: string) {
  const key = `${initial}${finalChar}`
  if (isAvailable(initial, finalChar)) {
    router.push(`/learn/${key}`)
  }
}

const filteredInitials = computed(() => {
  if (!searchQuery.value) return initials
  return initials.filter(i => i.includes(searchQuery.value.toLowerCase()))
})

const filteredFinals = computed(() => {
  if (!searchQuery.value) return finals
  return finals.filter(f => f.includes(searchQuery.value.toLowerCase()))
})
</script>

<template>
  <div class="pronunciation-map">
    <div class="map-header">
      <h3>发音地图</h3>
      <p>点击可学习的拼音单元开始练习（共 {{ availableCount }} 个发音单元）</p>
      <el-input
        v-model="searchQuery"
        placeholder="搜索拼音..."
        prefix-icon="Search"
        style="width: 300px; margin-top: 12px"
        clearable
      />
    </div>

    <!-- 图例 -->
    <div class="legend">
      <span class="legend-item"><span class="dot available"></span> 可学习</span>
      <span class="legend-item"><span class="dot locked"></span> 未开放</span>
      <span class="legend-item legend-note">* AI 录音检测当前已开放 50 个核心单元（详见发音库「核心对比」卡片）</span>
    </div>

    <!-- 声调说明 -->
    <div class="tone-legend">
      <h4>声调说明</h4>
      <div class="tone-items">
        <div v-for="(tone, idx) in tones" :key="idx" class="tone-item">
          <span class="tone-mark" :style="{ color: tone.color }">{{ tone.mark }}</span>
          <span>{{ tone.name }}</span>
        </div>
      </div>
    </div>

    <!-- 拼音矩阵 -->
    <div class="matrix-container">
      <div class="matrix-scroll">
        <table class="pinyin-table">
          <thead>
            <tr>
              <th class="corner-cell">声母＼韵母</th>
              <th v-for="f in filteredFinals" :key="f" class="final-header">{{ f }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="initial in filteredInitials" :key="initial">
              <td class="initial-header">{{ initial }}</td>
              <td
                v-for="f in filteredFinals"
                :key="f"
                class="pinyin-cell"
                :class="{ available: isAvailable(initial, f), locked: !isAvailable(initial, f) }"
                @click="handleClick(initial, f)"
              >
                <span v-if="isAvailable(initial, f)" class="cell-content">
                  <span class="character">{{ getCharacter(initial, f) }}</span>
                  <span class="pinyin">{{ initial }}{{ f }}</span>
                </span>
                <span v-else class="cell-dash">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pronunciation-map {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.map-header {
  margin-bottom: 20px;
}

.map-header h3 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.map-header p {
  margin: 8px 0 0;
  color: #909399;
  font-size: 14px;
}

.legend {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.dot.available {
  background: #409eff;
}

.dot.locked {
  background: #dcdfe6;
}

.legend-note {
  color: #909399;
  font-size: 12px;
}

.tone-legend {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.tone-legend h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #303133;
}

.tone-items {
  display: flex;
  gap: 32px;
}

.tone-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
}

.tone-mark {
  font-size: 20px;
  font-weight: bold;
}

.matrix-container {
  overflow-x: auto;
}

.matrix-scroll {
  min-width: fit-content;
}

.pinyin-table {
  border-collapse: collapse;
  width: 100%;
}

.pinyin-table th,
.pinyin-table td {
  border: 1px solid #ebeef5;
  text-align: center;
  padding: 8px 4px;
  font-size: 12px;
}

.corner-cell {
  background: #f5f7fa;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  position: sticky;
  left: 0;
  z-index: 2;
}

.final-header {
  background: #f5f7fa;
  font-weight: 600;
  color: #409eff;
  min-width: 48px;
}

.initial-header {
  background: #f5f7fa;
  font-weight: 600;
  color: #67c23a;
  position: sticky;
  left: 0;
  z-index: 1;
  white-space: nowrap;
}

.pinyin-cell {
  cursor: default;
  transition: all 0.2s;
  min-width: 48px;
  height: 48px;
}

.pinyin-cell.available {
  background: #ecf5ff;
  cursor: pointer;
}

.pinyin-cell.available:hover {
  background: #409eff;
  color: white;
  transform: scale(1.1);
  z-index: 1;
  position: relative;
  border-radius: 4px;
}

.pinyin-cell.available:hover .character,
.pinyin-cell.available:hover .pinyin {
  color: white;
}

.cell-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.character {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.pinyin {
  font-size: 10px;
  color: #909399;
}

.cell-dash {
  color: #dcdfe6;
}
</style>