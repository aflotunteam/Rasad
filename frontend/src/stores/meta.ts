import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { metaApi } from '@/services/api'
import type { Meta, RiskType } from '@/types/api'

export const useMetaStore = defineStore('meta', () => {
  const meta = ref<Meta | null>(null)
  const loading = ref(false)

  async function load(force = false) {
    if (meta.value && !force) return
    loading.value = true
    try {
      meta.value = await metaApi.get()
    } finally {
      loading.value = false
    }
  }

  const regionName = computed(() => {
    const map = new Map(meta.value?.regions.map((r) => [r.id, r.name]) ?? [])
    return (id: string | null | undefined) => (id ? (map.get(id) ?? id) : '—')
  })
  const regionShort = computed(() => {
    const map = new Map(meta.value?.regions.map((r) => [r.id, r.short_name]) ?? [])
    return (id: string | null | undefined) => (id ? (map.get(id) ?? id) : '—')
  })
  const sectorName = computed(() => {
    const map = new Map(meta.value?.sectors.map((s) => [s.id, s.name]) ?? [])
    return (id: string | null | undefined) => (id ? (map.get(id) ?? id) : '—')
  })
  const riskType = computed(() => {
    const map = new Map(meta.value?.risk_types.map((t) => [t.code, t]) ?? [])
    return (code: string | null | undefined): RiskType | undefined => (code ? map.get(code as RiskType['code']) : undefined)
  })
  const thresholds = computed(() => meta.value?.thresholds ?? { low: 40, high: 70, is_mvp_default: true })

  return { meta, loading, load, regionName, regionShort, sectorName, riskType, thresholds }
})
