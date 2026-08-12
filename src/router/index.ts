import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/map',
    },
    {
      path: '/home',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/map',
      name: 'map',
      component: () => import('@/views/PronunciationMap.vue'),
      meta: { title: '发音地图' },
    },
    {
      path: '/library',
      name: 'library',
      component: () => import('@/views/PronunciationLibrary.vue'),
      meta: { title: '发音库' },
    },
    {
      path: '/learn/:id',
      name: 'learn',
      component: () => import('@/views/LearningView.vue'),
      meta: { title: '发音学习' },
    },
    {
      path: '/feedback/:id',
      name: 'feedback',
      component: () => import('@/views/FeedbackView.vue'),
      meta: { title: '反馈系统' },
    },
    {
      path: '/progress',
      name: 'progress',
      component: () => import('@/views/ProgressView.vue'),
      meta: { title: '学习进度' },
    },
    {
      path: '/compare',
      name: 'compare',
      component: () => import('@/views/ComparisonView.vue'),
      meta: { title: '发音对比' },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/HistoryView.vue'),
      meta: { title: '学习记录' },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue'),
      meta: { title: '后台管理' },
    },
    {
      path: '/progress-manage',
      name: 'progress-manage',
      component: () => import('@/views/ProgressManagement.vue'),
      meta: { title: '进度管理' },
    },
  ],
})

export default router