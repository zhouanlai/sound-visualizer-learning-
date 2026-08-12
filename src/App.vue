<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const isCollapsed = ref(false)

const menuItems = [
  { path: '/map', icon: 'MapLocation', title: '发音地图', desc: '拼音矩阵总览' },
  { path: '/library', icon: 'Collection', title: '发音库', desc: '12个发音单元' },
  { path: '/learn/ma', icon: 'Microphone', title: '发音学习', desc: '学习-录音-反馈' },
  { path: '/feedback/ma', icon: 'DataAnalysis', title: '反馈系统', desc: '可视化分析' },
  { path: '/compare', icon: 'Switch', title: '发音对比', desc: '双录音对比' },
  { path: '/progress', icon: 'TrendCharts', title: '学习进度', desc: '进度概览' },
  { path: '/history', icon: 'Clock', title: '学习记录', desc: '练习历史' },
  { path: '/progress-manage', icon: 'Management', title: '进度管理', desc: '详细管理' },
  { path: '/admin', icon: 'Setting', title: '后台管理', desc: '内容管理' },
]

const currentTitle = computed(() => {
  const item = menuItems.find(m => route.path.startsWith(m.path))
  return item?.title || '看得见的声音'
})

const handleMenuClick = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="app-container">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="sidebar-header">
        <div class="logo-section">
          <el-icon :size="28" color="#409eff"><Microphone /></el-icon>
          <div v-if="!isCollapsed" class="logo-text">
            <h1>看得见的声音</h1>
            <p>智能发音学习平台</p>
          </div>
        </div>
        <el-button
          :icon="isCollapsed ? 'ArrowRight' : 'ArrowLeft'"
          text
          @click="isCollapsed = !isCollapsed"
          class="collapse-btn"
        />
      </div>

      <el-menu
        :default-active="route.path"
        :collapse="isCollapsed"
        class="sidebar-menu"
        @select="(path: string) => handleMenuClick(path)"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>
            <div class="menu-item-content">
              <span>{{ item.title }}</span>
              <small v-if="!isCollapsed">{{ item.desc }}</small>
            </div>
          </template>
        </el-menu-item>
      </el-menu>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <header class="top-header">
        <div class="header-left">
          <h2>{{ currentTitle }}</h2>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-button type="primary" :icon="'Microphone'" @click="router.push('/learn/ma')">
            开始练习
          </el-button>
        </div>
      </header>

      <div class="page-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 240px;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: white;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-text h1 {
  font-size: 16px;
  margin: 0;
  white-space: nowrap;
}

.logo-text p {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  margin: 2px 0 0;
  white-space: nowrap;
}

.collapse-btn {
  color: rgba(255, 255, 255, 0.6);
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  background: transparent;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 240px;
}

:deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.8);
  height: 56px;
  margin: 4px 8px;
  border-radius: 8px;
}

:deep(.el-menu-item:hover),
:deep(.el-menu-item.is-active) {
  background: rgba(64, 158, 255, 0.2);
  color: #409eff;
}

.menu-item-content {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}

.menu-item-content small {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
  overflow: hidden;
}

.top-header {
  background: white;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  z-index: 10;
}

.header-left h2 {
  margin: 0 0 4px;
  font-size: 18px;
  color: #303133;
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>