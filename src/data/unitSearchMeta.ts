/** 附录 A 12 单元搜索/地图元数据：IPA、部位、方法、问题标签 */
export interface UnitSearchMeta {
  ipa: string
  initial?: string
  final?: string
  tone?: string
  place: string[]
  method: string[]
  aspiration?: '送气' | '不送气' | '不适用'
  nasal?: boolean
  tags: string[]
  professional: Array<{ term: string; explain: string }>
  similar: string[]
}

export const PLACE_FILTERS = ['双唇', '舌尖中', '舌根', '舌面', '舌尖前', '舌尖后', '口腔'] as const
export const METHOD_FILTERS = ['塞音', '擦音', '鼻音', '边音', '元音', '塞擦音'] as const
export const TAG_FILTERS = ['n/l分不清', '四声不稳', '送气对比', '平翘舌', '圆唇元音', '开口元音'] as const

export const UNIT_SEARCH_META: Record<string, UnitSearchMeta> = {
  a: {
    ipa: 'a',
    final: 'a',
    place: ['口腔'],
    method: ['元音'],
    aspiration: '不适用',
    tags: ['开口元音', '元音'],
    professional: [
      { term: 'F1', explain: '第一共振峰，开口越大 F1 越高（约 700–900 Hz）。' },
      { term: 'Vowel Space', explain: '元音在 F1-F2 平面上的位置反映舌位高低前后。' },
    ],
    similar: ['i', 'u_u'],
  },
  i: {
    ipa: 'i',
    final: 'i',
    place: ['舌面', '口腔'],
    method: ['元音'],
    aspiration: '不适用',
    tags: ['开口元音', '元音'],
    professional: [
      { term: 'F2', explain: '第二共振峰高（约 2200–2600 Hz）对应舌位靠前。' },
    ],
    similar: ['a', 'u_u'],
  },
  u_u: {
    ipa: 'u / y',
    final: 'u / ü',
    place: ['口腔'],
    method: ['元音'],
    aspiration: '不适用',
    tags: ['圆唇元音', '元音'],
    professional: [
      { term: '圆唇', explain: 'u 舌位靠后；ü 舌面前高同时圆唇。' },
    ],
    similar: ['a', 'i'],
  },
  m: {
    ipa: 'm',
    initial: 'm',
    place: ['双唇'],
    method: ['鼻音'],
    aspiration: '不适用',
    nasal: true,
    tags: ['鼻音', '双唇'],
    professional: [
      { term: '鼻音', explain: '软腭下降，气流主要经鼻腔；捏鼻可验证。' },
    ],
    similar: ['n_l', 'ma'],
  },
  b_p: {
    ipa: 'p / pʰ',
    initial: 'b / p',
    place: ['双唇'],
    method: ['塞音'],
    aspiration: '送气',
    tags: ['送气对比', '双唇'],
    professional: [
      { term: 'VOT', explain: '送气塞音除阻后有一段浊音起始延迟（Voice Onset Time）。' },
    ],
    similar: ['d_t', 'g_k'],
  },
  d_t: {
    ipa: 't / tʰ',
    initial: 'd / t',
    place: ['舌尖中'],
    method: ['塞音'],
    aspiration: '送气',
    tags: ['送气对比'],
    professional: [
      { term: '成阻部位', explain: '舌尖抵上齿龈，与舌根音 g/k 部位不同。' },
    ],
    similar: ['b_p', 'n_l'],
  },
  n_l: {
    ipa: 'n / l',
    initial: 'n / l',
    place: ['舌尖中'],
    method: ['鼻音', '边音'],
    aspiration: '不适用',
    nasal: true,
    tags: ['n/l分不清'],
    professional: [
      { term: '边音', explain: 'l 时软腭抬起，气流从舌两侧通过；n 走鼻腔。' },
    ],
    similar: ['m', 'ma'],
  },
  g_k: {
    ipa: 'k / kʰ',
    initial: 'g / k',
    place: ['舌根'],
    method: ['塞音'],
    aspiration: '送气',
    tags: ['送气对比'],
    professional: [
      { term: '舌根塞音', explain: '舌根抬起抵软腭成阻。' },
    ],
    similar: ['b_p', 'd_t'],
  },
  j_q_x: {
    ipa: 'tɕ / tɕʰ / ɕ',
    initial: 'j / q / x',
    place: ['舌面'],
    method: ['塞擦音', '擦音'],
    aspiration: '送气',
    tags: ['舌面音'],
    professional: [
      { term: '舌面音', explain: '舌面前部接近硬腭；与平舌、翘舌部位不同。' },
    ],
    similar: ['z_zh'],
  },
  z_zh: {
    ipa: 'ts / tʂ',
    initial: 'z / zh',
    place: ['舌尖前', '舌尖后'],
    method: ['塞擦音', '擦音'],
    tags: ['平翘舌'],
    professional: [
      { term: '平舌/翘舌', explain: 'z/c/s 舌尖抵下齿背；zh/ch/sh 舌尖卷抵硬腭前。' },
    ],
    similar: ['j_q_x', 'n_l'],
  },
  ma_tone: {
    ipa: 'ma⁵⁵ ma³⁵ ma²¹⁴ ma⁵¹',
    initial: 'm',
    final: 'a',
    tone: '四声',
    place: ['双唇', '口腔'],
    method: ['鼻音', '元音'],
    tags: ['四声不稳'],
    professional: [
      { term: 'F0', explain: '基频曲线反映声调走向；上声 214 先降后升。' },
    ],
    similar: ['ma', 'm'],
  },
  ma: {
    ipa: 'ma⁵⁵',
    initial: 'm',
    final: 'a',
    tone: '阴平',
    place: ['双唇', '口腔'],
    method: ['鼻音', '元音'],
    nasal: true,
    tags: ['四声不稳', '完整闭环'],
    professional: [
      { term: '音节结构', explain: '声母 m + 韵母 a + 阴平调；首版核心检测任务。' },
    ],
    similar: ['m', 'a', 'ma_tone'],
  },
}

export const PROBLEM_KEYWORDS: Record<string, string[]> = {
  'n/l分不清': ['n', 'l', '鼻音', '边音', 'n_l', '那', '辣'],
  '四声不稳': ['四声', '声调', '妈', '麻', '马', '骂', 'ma_tone', 'ma'],
  '送气对比': ['送气', 'b', 'p', 'd', 't', 'g', 'k', 'b_p', 'd_t', 'g_k'],
  '平翘舌': ['平舌', '翘舌', 'z', 'zh', 'z_zh'],
  '圆唇元音': ['圆唇', 'u', 'ü', 'u_u', '五', '鱼'],
  '开口元音': ['开口', 'a', '啊'],
}
