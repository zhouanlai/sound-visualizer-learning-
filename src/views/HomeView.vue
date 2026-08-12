<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const features = [
  { icon: 'MapLocation', title: '发音地图', desc: '63个拼音字母的矩阵布局，一目了然', color: '#409eff', path: '/map' },
  { icon: 'Collection', title: '发音库', desc: '12个发音单元，系统化学习', color: '#67c23a', path: '/library' },
  { icon: 'Microphone', title: '智能录音', desc: '实时音频可视化，精准捕捉发音', color: '#e6a23c', path: '/learn/ma' },
  { icon: 'DataAnalysis', title: 'AI分析', desc: '深度学习模型评估发音质量', color: '#f56c6c', path: '/feedback/ma' },
  { icon: 'View', title: '3D可视化', desc: '口腔剖面动画，直观理解发音', color: '#9b59b6', path: '/feedback/ma' },
  { icon: 'TrendCharts', title: '学习进度', desc: '数据驱动，追踪学习轨迹', color: '#1abc9c', path: '/progress' },
]
</script>

<template>
  <div class="home-view">
    <div class="hero">
      <div class="hero-content">
        <h1>看得见的声音</h1>
        <p class="subtitle">智能发音学习平台</p>
        <p class="desc">通过多模态可视化技术，将抽象的语音知识转化为直观的视觉信息，帮助您快速掌握标准发音。</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" :icon="'MapLocation'" @click="router.push('/map')">发音地图</el-button>
          <el-button size="large" :icon="'Microphone'" @click="router.push('/learn/ma')">开始练习</el-button>
        </div>
      </div>
    </div>

    <div class="features-section">
      <h2>核心功能</h2>
      <div class="features-grid">
        <el-card v-for="f in features" :key="f.title" shadow="hover" class="feature-card" @click="router.push(f.path)">
          <div class="feature-icon" :style="{ background: f.color + '20', color: f.color }">
            <el-icon :size="32"><component :is="f.icon" /></el-icon>
          </div>
          <h3>{{ f.title }}</h3>
          <p>{{ f.desc }}</p>
        </el-card>
      </div>
    </div>

    <div class="tech-section">
      <h2>技术架构</h2>
      <div class="tech-grid">
        <div class="tech-item" v-for="t in [
          { name: 'Vue 3', desc: '前端框架' },
          { name: 'Three.js', desc: '3D可视化' },
          { name: 'FastAPI', desc: '后端服务' },
          { name: 'PyTorch', desc: '深度学习' },
          { name: 'Librosa', desc: '音频分析' },
          { name: 'Web Audio', desc: '实时录音' },
        ]" :key="t.name">
          <strong>{{ t.name }}</strong>
          <span>{{ t.desc }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-view { max-width: 1200px; margin: 0 auto; }
.hero { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border-radius: 16px; padding: 60px 40px; color: white; margin-bottom: 40px; }
.hero-content { max-width: 600px; }
.hero h1 { font-size: 42px; margin: 0; }
.subtitle { font-size: 20px; color: #409eff; margin: 8px 0 16px; }
.desc { font-size: 16px; color: rgba(255,255,255,0.8); line-height: 1.6; margin-bottom: 24px; }
.hero-actions { display: flex; gap: 12px; }
.features-section, .tech-section { margin-bottom: 40px; }
.features-section h2, .tech-section h2 { text-align: center; margin-bottom: 24px; color: #303133; }
.features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.feature-card { cursor: pointer; border-radius: 12px; transition: all 0.3s; text-align: center; }
.feature-card:hover { transform: translateY(-4px); }
.feature-icon { width: 64px; height: 64px; border-radius: 16px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px; }
.feature-card h3 { margin: 0 0 8px; color: #303133; }
.feature-card p { margin: 0; color: #909399; font-size: 14px; }
.tech-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; }
.tech-item { background: white; border-radius: 8px; padding: 16px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.tech-item strong { display: block; color: #409eff; font-size: 16px; margin-bottom: 4px; }
.tech-item span { color: #909399; font-size: 13px; }
</style>