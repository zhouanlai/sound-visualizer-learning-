<template>
  <footer class="site-footer">
    <div class="footer-grid">
      <div>
        <strong>看得见的声音</strong>
        <p>© {{ year }} 智能发音学习平台</p>
      </div>
      <div>
        <strong>使用边界</strong>
        <p>学习参考，不作为普通话等级认定或医学诊断依据。</p>
      </div>
      <div>
        <strong>隐私与数据</strong>
        <p>访客录音默认不长期保存；同意后才写入个人声音档案，可随时删除。</p>
      </div>
      <div>
        <strong>内容纠错</strong>
        <p>发现文字、声音或专业内容问题，请在页面底部反馈或联系：feedback@voice-learn.local</p>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
const year = new Date().getFullYear()
</script>

<style scoped>
.site-footer {
  margin-top: 32px;
  padding: 24px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
  font-size: 13px;
  color: #606266;
}
.footer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
strong { display: block; color: #303133; margin-bottom: 6px; }
p { margin: 0; line-height: 1.6; }
</style>
