/** 附录 A 首批 12 个完整发音单元（与后端 CORE_UNITS 一致） */
export const CORE_UNIT_IDS = [
  'a', 'i', 'u_u', 'm', 'b_p', 'd_t', 'n_l', 'g_k', 'j_q_x', 'z_zh', 'ma_tone', 'ma',
] as const

export type CoreUnitId = (typeof CORE_UNIT_IDS)[number]

export const FAQ_ITEMS = [
  { q: 'n 和 l 分不清怎么办？', unitId: 'n_l', keyword: 'n l' },
  { q: '四声不稳、听起来像同一个调？', unitId: 'ma_tone', keyword: '四声' },
  { q: '练一会儿就累、声音发紧？', unitId: 'm', keyword: '气息' },
]

export const HOME_ACTIONS = [
  { label: '搜一个音', desc: '输入汉字、拼音或问题', route: '/search', query: {} },
  { label: '看懂发音', desc: '从发音地图理解关系', route: '/map', query: {} },
  { label: '跟着练', desc: '进入示范单元跟读', route: '/learn/ma', query: {} },
  { label: '录音比较', desc: '完成检测并看差异', route: '/test', query: { unit: 'ma' } },
] as const

export interface PublishedUnit {
  id: string
  pinyin: string
  character: string
  category: string
  description: string
  conclusion: string
  detail: string
  mistakes: Array<{ title?: string; text?: string; phenomenon?: string; hint?: string }>
  steps: Array<{ title?: string; text?: string; duration?: string }>
  related: string[]
  status: string
  verified: boolean
  order: number
}
