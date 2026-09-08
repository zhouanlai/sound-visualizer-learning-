<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { feedbackApi } from '@/api'
import { useUserStore } from '@/stores/user'

const props = defineProps<{
  page: string
  unitId?: string
  type?: 'learning' | 'result' | 'content' | 'request'
}>()

const userStore = useUserStore()
const rating = ref<'yes' | 'no' | ''>('')
const message = ref('')
const submitting = ref(false)

async function submit() {
  if (!rating.value && !message.value.trim()) {
    ElMessage.warning('请选择是否看懂，或补充说明')
    return
  }
  submitting.value = true
  try {
    await feedbackApi.submit({
      userId: userStore.userId,
      type: props.type || 'learning',
      page: props.page,
      unitId: props.unitId || '',
      rating: rating.value,
      message: message.value.trim(),
    })
    ElMessage.success('感谢反馈，我们会尽快处理')
    rating.value = ''
    message.value = ''
  } catch {
    ElMessage.error('反馈提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-feedback">
    <h4>这页内容对你有帮助吗？</h4>
    <div class="rating-row">
      <el-radio-group v-model="rating">
        <el-radio value="yes">看懂了</el-radio>
        <el-radio value="no">还不明白</el-radio>
      </el-radio-group>
    </div>
    <el-input
      v-model="message"
      type="textarea"
      :rows="2"
      placeholder="可选：说明不清楚的位置、内容问题或希望增加的内容"
    />
    <el-button type="primary" size="small" :loading="submitting" @click="submit">提交反馈</el-button>
  </div>
</template>

<style scoped>
.page-feedback {
  margin-top: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}
.page-feedback h4 { margin: 0 0 12px; font-size: 14px; color: #303133; }
.rating-row { margin-bottom: 12px; }
</style>
