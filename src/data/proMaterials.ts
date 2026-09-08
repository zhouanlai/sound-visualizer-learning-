export const PRO_CATEGORIES = [
  { id: 'phonetics', name: '语音学', desc: '音位、声调与辨音' },
  { id: 'acoustics', name: '声学', desc: 'F0、共振峰、语谱图' },
  { id: 'physiology', name: '发声生理', desc: '呼吸、声带、共鸣、构音' },
  { id: 'methods', name: '测量方法', desc: '录音、标注与可靠性' },
]

export const PRO_MATERIALS = [
  {
    id: 'ipa-intro',
    title: 'IPA 与国际音标入门',
    category: 'phonetics',
    summary: '用符号精确描述汉语声母、韵母与声调，避免仅用汉字记录产生歧义。',
    scope: '适用于理解发音部位与方法；不能直接替代个人听感训练。',
    relatedUnits: ['a', 'i', 'm'],
    source: '语音学教材摘要（示意）',
    license: '学习引用',
  },
  {
    id: 'f0-tone',
    title: 'F0 曲线与四声',
    category: 'acoustics',
    summary: '阴平高平、阳平上升、上声降升、去声急降——可用 F0 曲线可视化对比。',
    scope: '可观察声调走向；环境噪声会影响提取精度。',
    relatedUnits: ['ma_tone', 'ma'],
    source: '声学分析示意',
    license: '学习引用',
  },
  {
    id: 'formant-vowel',
    title: 'F1/F2 与元音舌位',
    category: 'acoustics',
    summary: '开口元音 a 的 F1 较高；高前 i 的 F2 较高；u/ü 圆唇特征不同。',
    scope: '元音对比学习参考；首版元音比较检测待样本验证后开放。',
    relatedUnits: ['a', 'i', 'u_u'],
    source: '声学对比示意',
    license: '学习引用',
  },
  {
    id: 'vot-stop',
    title: 'VOT 与送气对比',
    category: 'methods',
    summary: 'b/p、d/t、g/k 等塞音可通过送气与否区分，VOT 是常用指标之一。',
    scope: '送气比较任务待规则验证后开放；当前以听感与口型练习为主。',
    relatedUnits: ['b_p', 'd_t', 'g_k'],
    source: '实验语音学方法摘要',
    license: '学习引用',
  },
]
