import { CORE_UNIT_IDS } from './coreUnits'
import { UNIT_SEARCH_META, type UnitSearchMeta } from './unitSearchMeta'

export type MapLayer = 'initial' | 'final' | 'tone' | 'syllable' | 'character'

export interface MapNode {
  id: string
  unitId: string
  layer: MapLayer
  name: string
  pinyin: string
  character: string
  conclusion: string
  meta: UnitSearchMeta
}

const LAYER_LABELS: Record<MapLayer, string> = {
  initial: '声母',
  final: '韵母',
  tone: '声调',
  syllable: '音节',
  character: '汉字',
}

const LAYER_ORDER: MapLayer[] = ['initial', 'final', 'tone', 'syllable', 'character']

/** 附录 A 单元在地图中的层级归类 */
const UNIT_LAYER: Record<string, MapLayer> = {
  m: 'initial',
  b_p: 'initial',
  d_t: 'initial',
  n_l: 'initial',
  g_k: 'initial',
  j_q_x: 'initial',
  z_zh: 'initial',
  a: 'final',
  i: 'final',
  u_u: 'final',
  ma_tone: 'tone',
  ma: 'character',
}

export function buildMapNodes(
  units: Array<{ id: string; pinyin: string; character: string; conclusion: string }>
): MapNode[] {
  return CORE_UNIT_IDS.map(id => {
    const u = units.find(x => x.id === id)
    const meta = UNIT_SEARCH_META[id]
    if (!u || !meta) return null
    return {
      id,
      unitId: id,
      layer: UNIT_LAYER[id] || 'syllable',
      name: u.character.split('/')[0] || u.id,
      pinyin: u.pinyin,
      character: u.character,
      conclusion: u.conclusion,
      meta,
    }
  }).filter(Boolean) as MapNode[]
}

export { LAYER_LABELS, LAYER_ORDER }
