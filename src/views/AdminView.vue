<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi, learningRecordApi } from '@/api'
import type { LearningRecord, AdminStats } from '@/types'

const activeTab = ref('content')
const units = ref([
  { id: 'ma', pinyin: 'mā', character: '妈', category: '声母', status: 'published', order: 1 },
  { id: 'ba', pinyin: 'bā', character: '八', category: '声母', status: 'published', order: 2 },
  { id: 'pa', pinyin: 'pā', character: '趴', category: '声母', status: 'published', order: 3 },
  { id: 'ta', pinyin: 'tā', character: '他', category: '声母', status: 'published', order: 4 },
  { id: 'yi', pinyin: 'yī', character: '一', category: '韵母', status: 'draft', order: 5 },
  { id: 'wu', pinyin: 'wǔ', character: '五', category: '韵母', status: 'draft', order: 6 },
])

const dialogVisible = ref(false)
const editingUnit = ref<any>(null)

function editUnit(unit: any) {
  editingUnit.value = { ...unit }
  dialogVisible.value = true
}

function saveUnit() {
  const idx = units.value.findIndex(u => u.id === editingUnit.value.id)
  if (idx >= 0) units.value[idx] = { ...editingUnit.value }
  dialogVisible.value = false
}

// ===== 数据统计（读数据库真实数据）=====
const stats = ref<AdminStats | null>(null)
const allRecords = ref<LearningRecord[]>([])
const statsLoading = ref(false)

async function loadStats() {
  statsLoading.value = true
  try {
    const [statsRes, recordsRes] = await Promise.all([
      adminApi.getStats(),
      adminApi.getAllLearningRecords(100),
    ])
    stats.value = statsRes.data
    allRecords.value = recordsRes.data
  } catch (err) {
    ElMessage.error('统计数据加载失败')
    console.error(err)
  } finally {
    statsLoading.value = false
  }
}

async function playRecordAudio(record: LearningRecord) {
  try {
    // 从数据库按需拉取录音二进制，转 blob URL 播放
    const url = await learningRecordApi.getRecordAudio(record.id)
    const audio = new Audio(url)
    audio.play().catch(() => {})
  } catch (err) {
    ElMessage.error('录音加载失败')
    console.error(err)
  }
}

// 切换到「数据统计」tab 时加载最新数据
watch(activeTab, (tab) => {
  if (tab === 'stats') loadStats()
})
</script>

<template>
  <div class="admin-view">
    <el-tabs v-model="activeTab" class="admin-tabs">
      <el-tab-pane label="内容管理" name="content">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>发音单元管理</span>
              <el-button type="primary" :icon="'Plus'" size="small">添加单元</el-button>
            </div>
          </template>
          <el-table :data="units" stripe>
            <el-table-column prop="order" label="序号" width="60" />
            <el-table-column prop="pinyin" label="拼音" width="100"><template #default="{ row }"><span style="color:#409eff;font-weight:600;">{{ row.pinyin }}</span></template></el-table-column>
            <el-table-column prop="character" label="汉字" width="80" />
            <el-table-column prop="category" label="分类" width="80" />
            <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">{{ row.status === 'published' ? '已发布' : '草稿' }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button size="small" :icon="'Edit'" @click="editUnit(row)">编辑</el-button>
                <el-button size="small" :icon="'VideoPlay'">预览</el-button>
                <el-button size="small" type="danger" :icon="'Delete'">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="媒体管理" name="media">
        <el-card shadow="hover">
          <template #header><span>媒体资源</span></template>
          <el-upload drag action="#" accept="audio/*,video/*" :auto-upload="false">
            <el-icon :size="48"><UploadFilled /></el-icon>
            <div>拖拽文件到此处或<em>点击上传</em></div>
            <template #tip><div class="el-upload__tip">支持音频(mp3/wav)和视频(mp4/webm)格式</div></template>
          </el-upload>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="数据统计" name="stats">
        <div v-loading="statsLoading">
          <div class="stats-grid">
            <el-card v-for="item in [
              { label: '总用户', value: stats ? String(stats.totalUsers) : '-', icon: 'User' },
              { label: '今日练习', value: stats ? String(stats.todayRecords) : '-', icon: 'Microphone' },
              { label: '平均评分', value: stats ? String(stats.averageScore) : '-', icon: 'TrendCharts' },
              { label: '完成率', value: stats ? stats.completionRate + '%' : '-', icon: 'CircleCheck' },
            ]" :key="item.label" shadow="hover" class="stat-card">
              <el-icon :size="28" color="#409eff"><component :is="item.icon" /></el-icon>
              <div class="stat-val">{{ item.value }}</div>
              <div class="stat-lbl">{{ item.label }}</div>
            </el-card>
          </div>

          <el-card shadow="hover" class="records-card">
            <template #header><span>学习记录（数据库）</span></template>
            <el-table :data="allRecords" stripe empty-text="暂无学习记录">
              <el-table-column label="时间" width="170"><template #default="{ row }">{{ new Date(row.createdAt).toLocaleString() }}</template></el-table-column>
              <el-table-column label="用户" prop="userId" width="140" show-overflow-tooltip />
              <el-table-column label="拼音" width="90"><template #default="{ row }"><span style="color:#409eff;font-weight:600;">{{ row.pinyin }}</span></template></el-table-column>
              <el-table-column label="汉字" prop="character" width="70" />
              <el-table-column label="评分" width="90"><template #default="{ row }"><el-tag :type="row.score >= 80 ? 'success' : row.score >= 60 ? 'warning' : 'danger'">{{ row.score }}</el-tag></template></el-table-column>
              <el-table-column label="准确度" width="90"><template #default="{ row }">{{ row.accuracy }}%</template></el-table-column>
              <el-table-column label="反馈" prop="feedback" show-overflow-tooltip />
              <el-table-column label="操作" width="110">
                <template #default="{ row }">
                  <el-button size="small" :icon="'VideoPlay'" @click="playRecordAudio(row)">播放录音</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="dialogVisible" title="编辑发音单元" width="500px">
      <el-form v-if="editingUnit" label-width="80px">
        <el-form-item label="拼音"><el-input v-model="editingUnit.pinyin" /></el-form-item>
        <el-form-item label="汉字"><el-input v-model="editingUnit.character" /></el-form-item>
        <el-form-item label="分类"><el-select v-model="editingUnit.category"><el-option label="声母" value="声母" /><el-option label="韵母" value="韵母" /><el-option label="声调" value="声调" /></el-select></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUnit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-view { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.admin-tabs { min-height: 500px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.records-card { margin-top: 16px; border-radius: 12px; }
.stat-card { text-align: center; border-radius: 12px; }
.stat-card :deep(.el-card__body) { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 24px; }
.stat-val { font-size: 28px; font-weight: 700; color: #303133; }
.stat-lbl { font-size: 13px; color: #909399; }
</style>