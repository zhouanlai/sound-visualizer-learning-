import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '首页' } },
    { path: '/search', name: 'search', component: () => import('@/views/SearchResultsView.vue'), meta: { title: '搜索结果' } },
    { path: '/map', name: 'map', component: () => import('@/views/PronunciationMap.vue'), meta: { title: '发音地图' } },
    { path: '/principles', name: 'principles', component: () => import('@/views/PronunciationPrinciples.vue'), meta: { title: '发音原理' } },
    { path: '/library', name: 'library', component: () => import('@/views/PronunciationLibrary.vue'), meta: { title: '发音库' } },
    { path: '/materials', name: 'materials', component: () => import('@/views/ProfessionalMaterials.vue'), meta: { title: '专业资料' } },
    { path: '/test', name: 'test', component: () => import('@/views/TestCenterView.vue'), meta: { title: '检测中心' } },
    { path: '/learn/:id', name: 'learn', component: () => import('@/views/LearningView.vue'), meta: { title: '示范单元' } },
    { path: '/feedback/:id', name: 'feedback', component: () => import('@/views/FeedbackView.vue'), meta: { title: '检测结果' } },
    { path: '/archive', name: 'archive', component: () => import('@/views/HistoryView.vue'), meta: { title: '我的声音档案' } },
    { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue'), meta: { title: '后台管理' } },
    // 兼容旧路由
    { path: '/home', redirect: '/' },
    { path: '/history', redirect: '/archive' },
    { path: '/progress', redirect: '/archive' },
    { path: '/compare', redirect: '/archive' },
    { path: '/progress-manage', redirect: '/archive' },
  ],
})

export default router
