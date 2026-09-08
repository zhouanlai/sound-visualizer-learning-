<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { unitsApi, adminApi, mediaApi, learningRecordApi } from '@/api'
import type { CmsUnit, LearningRecord, UserFeedbackItem } from '@/types'

const activeTab = ref('content')
const units = ref<CmsUnit[]>([])
const feedbacks = ref<UserFeedbackItem[]>([])
const allRecords = ref<LearningRecord[]>([])
const stats = ref<any>(null)
const loading = ref(false)

const dialogVisible = ref(false)
const editingUnit = ref<Partial<CmsUnit> | null>(null)

async function loadUnits() {
  const res = await unitsApi.list()
  units.value = res.data
}

async function loadFeedbacks() {
  const res = await adminApi.getFeedbacks()
  feedbacks.value = res.data
}

async function loadStats() {
  loading.value = true
  try {
    const [s, r] = await Promise.all([adminApi.getStats(), adminApi.getAllLearningRecords(100)])
    stats.value = s.data
    allRecords.value = r.data
  } finally {
    loading.value = false
  }
}

onMounted(loadUnits)

watch(activeTab, (tab) => {
  if (tab === 'stats') loadStats()
  if (tab === 'feedback') loadFeedbacks()
})

function openCreate() {
  editingUnit.value = { status: 'draft', verified: false, category: '声母', order: units.value.length + 1 }
  dialogVisible.value = true
}

function editUnit(u: CmsUnit) {
  editingUnit.value = { ...u }
  dialogVisible.value = true
}

async function saveUnit() {
  if (!editingUnit.value) return
  try {
    if (editingUnit.value.id) {
      await unitsApi.update(editingUnit.value.id, editingUnit.value)
    } else {
      await unitsApi.create(editingUnit.value)
    }
    dialogVisible.value = false
    await loadUnits()
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败')
  }
}

async function removeUnit(id: string) {
  try {
    await unitsApi.delete(id)
    await loadUnits()
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

async function preview(id: string) {
  window.open(`/learn/${id}`, '_blank')
}

async function onMediaUpload(file: File) {
  try {
    await mediaApi.upload(file, 'audio')
    ElMessage.success('上传成功')
  } catch {
    ElMessage.error('上传失败')
  }
  return false
}

async function handleFeedback(id: string, status: 'adopted' | 'rejected') {
  await adminApi.updateFeedback(id, status, status === 'adopted' ? '已采纳' : '暂不采纳')
  await loadFeedbacks()
}
</script>

<template>
  <div class="admin-view">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="内容管理" name="content">
        <el-card>
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>发音单元（CMS）</span>
              <el-button type="primary" size="small" @click="openCreate">添加单元</el-button>
            </div>
          </template>
          <el-table :data="units" stripe>
            <el-table-column prop="order" label="#" width="50" />
            <el-table-column prop="pinyin" label="拼音" width="100" />
            <el-table-column prop="character" label="汉字" width="80" />
            <el-table-column prop="category" label="分类" width="80" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220">
              <template #default="{ row }">
                <el-button size="small" @click="editUnit(row)">编辑</el-button>
                <el-button size="small" @click="preview(row.id)">预览</el-button>
                <el-button size="small" type="danger" @click="removeUnit(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="媒体管理" name="media">
        <el-upload drag :auto-upload="true" :before-upload="onMediaUpload" accept="audio/*,image/*">
          <el-icon :size="48"><UploadFilled /></el-icon>
          <div>上传音频/图片（写入 uploads/）</div>
        </el-upload>
      </el-tab-pane>

      <el-tab-pane label="用户反馈" name="feedback">
        <el-table :data="feedbacks" stripe>
          <el-table-column prop="createdAt" label="时间" width="170" />
          <el-table-column prop="page" label="页面" width="120" />
          <el-table-column prop="rating" label="评价" width="80" />
          <el-table-column prop="message" label="内容" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="90" />
          <el-table-column label="处理" width="180">
            <template #default="{ row }">
              <el-button size="small" @click="handleFeedback(row.id, 'adopted')">采纳</el-button>
              <el-button size="small" @click="handleFeedback(row.id, 'rejected')">暂不采纳</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="数据统计" name="stats">
        <div v-loading="loading" class="stats-grid">
          <el-card v-for="item in [
            { label: '总用户', value: stats?.totalUsers ?? '-' },
            { label: '今日练习', value: stats?.todayRecords ?? '-' },
            { label: '平均评分', value: stats?.averageScore ?? '-' },
          ]" :key="item.label">
            <div class="stat-val">{{ item.value }}</div>
            <div class="stat-lbl">{{ item.label }}</div>
          </el-card>
        </div>
        <el-table :data="allRecords" stripe style="margin-top:16px">
          <el-table-column label="时间"><template #default="{ row }">{{ new Date(row.createdAt).toLocaleString() }}</template></el-table-column>
          <el-table-column prop="unitId" label="单元" />
          <el-table-column prop="score" label="评分" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="dialogVisible" title="编辑单元" width="520px">
      <el-form v-if="editingUnit" label-width="80px">
        <el-form-item label="ID"><el-input v-model="editingUnit.id" :disabled="!!editingUnit.id" /></el-form-item>
        <el-form-item label="拼音"><el-input v-model="editingUnit.pinyin" /></el-form-item>
        <el-form-item label="汉字"><el-input v-model="editingUnit.character" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="editingUnit.category" /></el-form-item>
        <el-form-item label="结论"><el-input v-model="editingUnit.conclusion" type="textarea" /></el-form-item>
        <el-form-item label="详情"><el-input v-model="editingUnit.detail" type="textarea" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editingUnit.status"><el-option label="草稿" value="draft" /><el-option label="已发布" value="published" /></el-select>
        </el-form-item>
        <el-form-item label="已验证"><el-switch v-model="editingUnit.verified" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUnit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-view { background: #fff; border-radius: 12px; padding: 24px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stat-val { font-size: 24px; font-weight: 700; }
.stat-lbl { color: #909399; font-size: 13px; }
</style>
