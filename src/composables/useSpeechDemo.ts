import { ref } from 'vue'

export const TTS_DISCLAIMER = '系统语音合成示意，非正式授权示范音。正式示范将以审核通过的录音替换。'

export function useSpeechDemo() {
  const isPlaying = ref(false)
  const mode = ref<'normal' | 'slow' | null>(null)

  function speak(text: string, speed: 'normal' | 'slow' = 'normal') {
    if (!('speechSynthesis' in window)) {
      return Promise.reject(new Error('浏览器不支持语音合成'))
    }
    speechSynthesis.cancel()
    isPlaying.value = true
    mode.value = speed
    return new Promise<void>((resolve, reject) => {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'zh-CN'
      utterance.rate = speed === 'slow' ? 0.55 : 0.85
      utterance.pitch = 1
      const voices = speechSynthesis.getVoices()
      const zh = voices.find(v => v.lang.startsWith('zh'))
      if (zh) utterance.voice = zh
      utterance.onend = () => {
        isPlaying.value = false
        mode.value = null
        resolve()
      }
      utterance.onerror = () => {
        isPlaying.value = false
        mode.value = null
        reject(new Error('播放失败'))
      }
      speechSynthesis.speak(utterance)
    })
  }

  function stop() {
    speechSynthesis.cancel()
    isPlaying.value = false
    mode.value = null
  }

  return { isPlaying, mode, speak, stop, disclaimer: TTS_DISCLAIMER }
}
