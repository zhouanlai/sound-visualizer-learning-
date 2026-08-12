<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { AVLine, AVBars, AVCircle, AVWaveform, AVMedia } from 'vue-audio-visual'

// 音频状态
const isRecording = ref(false)
const isPlaying = ref(false)
const audioContext = ref<AudioContext | null>(null)
const mediaStream = ref<MediaStream | null>(null)
const mediaRecorder = ref<MediaRecorder | null>(null)
const audioChunks = ref<Blob[]>([])
const audioUrl = ref<string>('')
const audioElement = ref<HTMLAudioElement | null>(null)

// 可视化状态
const visualizationType = ref<'waveform' | 'spectrum' | 'circle' | 'bars'>('waveform')
const showVisualization = ref(true)

// 发音分析状态
const analysisResult = ref<any>(null)
const isAnalyzing = ref(false)

// 录音控制
const startRecording = async () => {
  try {
    audioContext.value = new (window.AudioContext || (window as any).webkitAudioContext)()
    mediaStream.value = await navigator.mediaDevices.getUserMedia({ audio: true })
    
    mediaRecorder.value = new MediaRecorder(mediaStream.value)
    audioChunks.value = []
    
    mediaRecorder.value.ondataavailable = (event) => {
      audioChunks.value.push(event.data)
    }
    
    mediaRecorder.value.onstop = () => {
      const audioBlob = new Blob(audioChunks.value, { type: 'audio/wav' })
      audioUrl.value = URL.createObjectURL(audioBlob)
      
      // 停止所有音轨
      if (mediaStream.value) {
        mediaStream.value.getTracks().forEach(track => track.stop())
      }
    }
    
    mediaRecorder.value.start()
    isRecording.value = true
  } catch (error) {
    console.error('录音失败:', error)
    alert('无法访问麦克风，请检查权限设置。')
  }
}

const stopRecording = () => {
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop()
    isRecording.value = false
  }
}

// 播放控制
const playAudio = () => {
  if (audioElement.value && audioUrl.value) {
    audioElement.value.play()
    isPlaying.value = true
  }
}

const stopAudio = () => {
  if (audioElement.value) {
    audioElement.value.pause()
    audioElement.value.currentTime = 0
    isPlaying.value = false
  }
}

// 发音分析
const analyzePronunciation = async () => {
  if (!audioUrl.value) {
    alert('请先录制音频')
    return
  }
  
  isAnalyzing.value = true
  
  // 模拟分析过程
  setTimeout(() => {
    analysisResult.value = {
      score: Math.floor(Math.random() * 40) + 60, // 60-100分
      feedback: [
        '发音清晰度良好',
        '语速适中',
        '音调变化自然',
        '建议注意某些音节的发音'
      ],
      details: {
        clarity: Math.floor(Math.random() * 20) + 80,
        speed: Math.floor(Math.random() * 20) + 80,
        tone: Math.floor(Math.random() * 20) + 80
      }
    }
    isAnalyzing.value = false
  }, 2000)
}

// 清除录音
const clearRecording = () => {
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
    audioUrl.value = ''
    analysisResult.value = null
    isPlaying.value = false
  }
}

// 生命周期
onMounted(() => {
  // 初始化
})

onUnmounted(() => {
  // 清理资源
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
  }
  if (mediaStream.value) {
    mediaStream.value.getTracks().forEach(track => track.stop())
  }
})
</script>

<template>
  <div class="pronunciation-learning">
    <h1>发音学习平台</h1>
    
    <!-- 录音控制区域 -->
    <section class="recording-section">
      <h2>录音控制</h2>
      <div class="controls">
        <button 
          @click="isRecording ? stopRecording() : startRecording()"
          :class="{ recording: isRecording }"
          class="record-btn"
        >
          {{ isRecording ? '停止录音' : '开始录音' }}
        </button>
        
        <button 
          v-if="audioUrl" 
          @click="isPlaying ? stopAudio() : playAudio()"
          class="play-btn"
        >
          {{ isPlaying ? '停止播放' : '播放录音' }}
        </button>
        
        <button 
          v-if="audioUrl" 
          @click="clearRecording"
          class="clear-btn"
        >
          清除录音
        </button>
      </div>
      
      <!-- 隐藏的音频元素 -->
      <audio 
        v-if="audioUrl" 
        ref="audioElement" 
        :src="audioUrl" 
        @ended="isPlaying = false"
      ></audio>
    </section>
    
    <!-- 可视化区域 -->
    <section class="visualization-section" v-if="showVisualization">
      <h2>语音可视化</h2>
      
      <!-- 可视化类型选择 -->
      <div class="viz-type-selector">
        <button 
          @click="visualizationType = 'waveform'"
          :class="{ active: visualizationType === 'waveform' }"
        >
          波形图
        </button>
        <button 
          @click="visualizationType = 'spectrum'"
          :class="{ active: visualizationType === 'spectrum' }"
        >
          频谱图
        </button>
        <button 
          @click="visualizationType = 'circle'"
          :class="{ active: visualizationType === 'circle' }"
        >
          圆形图
        </button>
        <button 
          @click="visualizationType = 'bars'"
          :class="{ active: visualizationType === 'bars' }"
        >
          柱状图
        </button>
      </div>
      
      <!-- 可视化显示 -->
      <div class="visualization-display">
        <!-- 波形图 -->
        <div v-if="visualizationType === 'waveform'" class="viz-container">
          <h3>实时波形图</h3>
          <AVLine 
            v-if="audioUrl"
            :src="audioUrl"
            :line-width="2"
            line-color="#4CAF50"
            :canv-width="600"
            :canv-height="200"
          ></AVLine>
          <div v-else class="placeholder">
            请先录制音频以查看波形图
          </div>
        </div>
        
        <!-- 频谱图 -->
        <div v-if="visualizationType === 'spectrum'" class="viz-container">
          <h3>频谱分析图</h3>
          <AVBars 
            v-if="audioUrl"
            :src="audioUrl"
            :bar-color="['#FF5722', '#FF9800', '#FFC107']"
            caps-color="#FFF"
            :caps-height="2"
            :canv-width="600"
            :canv-height="200"
          ></AVBars>
          <div v-else class="placeholder">
            请先录制音频以查看频谱图
          </div>
        </div>
        
        <!-- 圆形图 -->
        <div v-if="visualizationType === 'circle'" class="viz-container">
          <h3>圆形可视化</h3>
          <AVCircle 
            v-if="audioUrl"
            :src="audioUrl"
            :outline-width="0"
            :progress-width="5"
            :outline-meter-space="5"
            :playtime="true"
            playtime-font="18px Monaco"
            :canv-width="300"
            :canv-height="300"
          ></AVCircle>
          <div v-else class="placeholder">
            请先录制音频以查看圆形图
          </div>
        </div>
        
        <!-- 柱状图 -->
        <div v-if="visualizationType === 'bars'" class="viz-container">
          <h3>柱状频谱图</h3>
          <AVWaveform 
            v-if="audioUrl"
            :src="audioUrl"
            :canv-width="600"
            :canv-height="200"
            played-line-color="#2196F3"
            noplayed-line-color="#BBDEFB"
          ></AVWaveform>
          <div v-else class="placeholder">
            请先录制音频以查看柱状图
          </div>
        </div>
      </div>
    </section>
    
    <!-- 发音分析区域 -->
    <section class="analysis-section">
      <h2>发音分析</h2>
      
      <button 
        @click="analyzePronunciation"
        :disabled="!audioUrl || isAnalyzing"
        class="analyze-btn"
      >
        {{ isAnalyzing ? '分析中...' : '分析发音' }}
      </button>
      
      <!-- 分析结果 -->
      <div v-if="analysisResult" class="analysis-result">
        <h3>分析结果</h3>
        
        <div class="score-section">
          <div class="score-circle">
            <span class="score">{{ analysisResult.score }}</span>
            <span class="label">总分</span>
          </div>
        </div>
        
        <div class="details-section">
          <h4>详细评分</h4>
          <div class="detail-item">
            <span class="detail-label">清晰度:</span>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: analysisResult.details.clarity + '%' }"
              ></div>
            </div>
            <span class="detail-value">{{ analysisResult.details.clarity }}%</span>
          </div>
          
          <div class="detail-item">
            <span class="detail-label">语速:</span>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: analysisResult.details.speed + '%' }"
              ></div>
            </div>
            <span class="detail-value">{{ analysisResult.details.speed }}%</span>
          </div>
          
          <div class="detail-item">
            <span class="detail-label">音调:</span>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: analysisResult.details.tone + '%' }"
              ></div>
            </div>
            <span class="detail-value">{{ analysisResult.details.tone }}%</span>
          </div>
        </div>
        
        <div class="feedback-section">
          <h4>改进建议</h4>
          <ul>
            <li v-for="(feedback, index) in analysisResult.feedback" :key="index">
              {{ feedback }}
            </li>
          </ul>
        </div>
      </div>
    </section>
    
    <!-- 使用说明 -->
    <section class="instructions-section">
      <h2>使用说明</h2>
      <ol>
        <li>点击"开始录音"按钮，对着麦克风说话</li>
        <li>说完后点击"停止录音"</li>
        <li>可以选择不同的可视化类型查看语音特征</li>
        <li>点击"分析发音"获取发音评估和改进建议</li>
        <li>可以多次录音练习，不断提高发音水平</li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.pronunciation-learning {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

h1 {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 2rem;
  font-size: 2.5rem;
}

h2 {
  color: #34495e;
  border-bottom: 2px solid #3498db;
  padding-bottom: 0.5rem;
  margin-top: 2rem;
}

section {
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.controls {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}

button {
  padding: 0.8rem 1.5rem;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.record-btn {
  background-color: #e74c3c;
  color: white;
}

.record-btn:hover {
  background-color: #c0392b;
}

.record-btn.recording {
  background-color: #95a5a6;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

.play-btn {
  background-color: #2ecc71;
  color: white;
}

.play-btn:hover {
  background-color: #27ae60;
}

.clear-btn {
  background-color: #95a5a6;
  color: white;
}

.clear-btn:hover {
  background-color: #7f8c8d;
}

.analyze-btn {
  background-color: #3498db;
  color: white;
  margin-top: 1rem;
}

.analyze-btn:hover:not(:disabled) {
  background-color: #2980b9;
}

.analyze-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.viz-type-selector {
  display: flex;
  gap: 0.5rem;
  margin: 1rem 0;
  flex-wrap: wrap;
}

.viz-type-selector button {
  background-color: #ecf0f1;
  color: #2c3e50;
  border: 2px solid #bdc3c7;
}

.viz-type-selector button.active {
  background-color: #3498db;
  color: white;
  border-color: #2980b9;
}

.visualization-display {
  margin-top: 1rem;
}

.viz-container {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  background-color: #f9f9f9;
}

.viz-container h3 {
  margin-top: 0;
  color: #2c3e50;
}

.placeholder {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #ecf0f1;
  border-radius: 5px;
  color: #7f8c8d;
  font-style: italic;
}

.analysis-result {
  margin-top: 1.5rem;
  padding: 1.5rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  border-left: 5px solid #3498db;
}

.score-section {
  text-align: center;
  margin-bottom: 2rem;
}

.score-circle {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3498db, #2ecc71);
  color: white;
}

.score {
  font-size: 2.5rem;
  font-weight: bold;
  line-height: 1;
}

.label {
  font-size: 0.9rem;
  opacity: 0.9;
}

.details-section {
  margin-bottom: 2rem;
}

.detail-item {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
  gap: 1rem;
}

.detail-label {
  min-width: 80px;
  font-weight: 600;
  color: #2c3e50;
}

.progress-bar {
  flex-grow: 1;
  height: 20px;
  background-color: #ecf0f1;
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3498db, #2ecc71);
  border-radius: 10px;
  transition: width 0.5s ease;
}

.detail-value {
  min-width: 50px;
  text-align: right;
  font-weight: 600;
  color: #2c3e50;
}

.feedback-section ul {
  list-style-type: none;
  padding: 0;
}

.feedback-section li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
  position: relative;
  padding-left: 1.5rem;
}

.feedback-section li:before {
  content: "•";
  color: #3498db;
  font-weight: bold;
  position: absolute;
  left: 0;
}

.instructions-section ol {
  padding-left: 1.5rem;
}

.instructions-section li {
  margin-bottom: 0.5rem;
  line-height: 1.6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .pronunciation-learning {
    padding: 1rem;
  }
  
  h1 {
    font-size: 2rem;
  }
  
  .controls {
    flex-direction: column;
  }
  
  .viz-type-selector {
    flex-direction: column;
  }
  
  .detail-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .progress-bar {
    width: 100%;
  }
}
</style>