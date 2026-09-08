import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { unitsApi } from '@/api'
import { CORE_UNIT_IDS, type PublishedUnit } from '@/data/coreUnits'
import { UNIT_SEARCH_META, PROBLEM_KEYWORDS, type UnitSearchMeta } from '@/data/unitSearchMeta'

export interface SearchOptions {
  category?: string
  place?: string
  method?: string
  tag?: string
}

export const useUnitsStore = defineStore('units', () => {
  const publishedUnits = ref<PublishedUnit[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const coreUnits = computed(() =>
    publishedUnits.value
      .filter(u => CORE_UNIT_IDS.includes(u.id as any))
      .sort((a, b) => CORE_UNIT_IDS.indexOf(a.id as any) - CORE_UNIT_IDS.indexOf(b.id as any))
  )

  async function fetchPublished() {
    loading.value = true
    error.value = null
    try {
      const res = await unitsApi.list('published')
      publishedUnits.value = res.data as PublishedUnit[]
    } catch (e) {
      error.value = '加载单元失败'
      console.error(e)
    } finally {
      loading.value = false
    }
  }

  async function getUnit(id: string): Promise<PublishedUnit | null> {
    if (!publishedUnits.value.length) await fetchPublished()
    const cached = publishedUnits.value.find(u => u.id === id)
    if (cached) return cached
    try {
      const res = await unitsApi.getById(id)
      return res.data as PublishedUnit
    } catch {
      return null
    }
  }

  function getMeta(id: string): UnitSearchMeta | undefined {
    return UNIT_SEARCH_META[id]
  }

  function unitLabel(id: string): string {
    const u = publishedUnits.value.find(x => x.id === id)
    return u ? `${u.character}（${u.pinyin}）` : id
  }

  function matchesKeyword(u: PublishedUnit, q: string): boolean {
    const meta = UNIT_SEARCH_META[u.id]
    const lower = q.toLowerCase()
    const fields = [
      u.id, u.pinyin, u.character, u.conclusion, u.description, u.category,
      meta?.ipa || '',
      meta?.initial || '',
      meta?.final || '',
      meta?.tone || '',
      ...(meta?.place || []),
      ...(meta?.method || []),
      ...(meta?.tags || []),
    ]
    if (fields.some(f => String(f).toLowerCase().includes(lower))) return true
    for (const [tag, keys] of Object.entries(PROBLEM_KEYWORDS)) {
      if (tag.includes(q) || q.includes(tag)) {
        if (keys.some(k => u.id.includes(k) || u.character.includes(k) || u.conclusion.includes(k))) return true
      }
    }
    return false
  }

  function search(keyword: string, options: SearchOptions = {}): PublishedUnit[] {
    let list = coreUnits.value
    if (options.category && options.category !== 'all') {
      list = list.filter(u => u.category === options.category)
    }
    if (options.place) {
      list = list.filter(u => UNIT_SEARCH_META[u.id]?.place.includes(options.place!))
    }
    if (options.method) {
      list = list.filter(u => UNIT_SEARCH_META[u.id]?.method.includes(options.method!))
    }
    if (options.tag) {
      list = list.filter(u => UNIT_SEARCH_META[u.id]?.tags.includes(options.tag!))
    }
    const q = keyword.trim()
    if (!q) return list
    return list.filter(u => matchesKeyword(u, q))
  }

  function findSimilar(keyword: string, limit = 3): PublishedUnit[] {
    const q = keyword.trim().toLowerCase()
    if (!q) return coreUnits.value.slice(0, limit)
    const scored = coreUnits.value.map(u => {
      let score = 0
      if (matchesKeyword(u, q)) score += 10
      const meta = UNIT_SEARCH_META[u.id]
      if (meta) {
        for (const tag of meta.tags) {
          if (tag.includes(q) || q.includes(tag)) score += 3
        }
        for (const p of meta.place) {
          if (p.includes(q)) score += 2
        }
      }
      return { u, score }
    })
    return scored
      .filter(x => x.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
      .map(x => x.u)
  }

  return {
    publishedUnits, coreUnits, loading, error,
    fetchPublished, getUnit, getMeta, unitLabel, search, findSimilar,
  }
})
