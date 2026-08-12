declare module 'vue-audio-visual' {
  import { Plugin, DefineComponent } from 'vue'
  const VueAudioVisual: Plugin
  export default VueAudioVisual
  export const AVLine: DefineComponent<any, any, any>
  export const AVBars: DefineComponent<any, any, any>
  export const AVCircle: DefineComponent<any, any, any>
  export const AVWaveform: DefineComponent<any, any, any>
  export const AVMedia: DefineComponent<any, any, any>
}
