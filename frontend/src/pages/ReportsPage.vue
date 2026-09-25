<script setup lang="ts">
import { FilePlus2 } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ReportPreview from '@/components/reports/ReportPreview.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { reportsApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { useUiStore } from '@/stores/ui'
import type { ReportListItem, ReportResult } from '@/types/api'
import { dateTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()
const auth = useAuthStore()
const ui = useUiStore()

const TYPES = [
  { key: 'subject', label: 'Subyekt hisoboti' },
  { key: 'region', label: 'Hududiy hisobot' },
  { key: 'sector', label: 'Tarmoq hisoboti' },
  { key: 'risk_type', label: 'Xavf turi hisoboti' },
  { key: 'periodic', label: 'Davriy hisobot' },
]

const type = ref('region')
const param = ref(auth.regionScope ?? 'NG')
const creating = ref(false)
const list = ref<ReportListItem[]>([])
const current = ref<ReportResult | null>(null)
const loadingPreview = ref(false)

const paramOptions = computed(() => {
  if (type.value === 'region') return (meta.meta?.regions ?? []).filter((r) => !auth.regionScope || r.id === auth.regionScope).map((r) => ({ v: r.id, l: r.name }))
  if (type.value === 'sector') return (meta.meta?.sectors ?? []).map((s) => ({ v: s.id, l: s.name }))
  if (type.value === 'risk_type') return (meta.meta?.risk_types ?? []).map((t) => ({ v: t.code, l: `${t.code} — ${t.name}` }))
  return []
})

watch(type, (t) => {
  param.value = t === 'subject' ? 'SUB-000125' : (paramOptions.value[0]?.v ?? '')
})

async function loadList() {
  list.value = await reportsApi.list().catch(() => [])
}

async function open(id: number) {
  loadingPreview.value = true
  try {
    current.value = await reportsApi.get(id)
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Hisobotni ochib bo‘lmadi', 'error')
  } finally {
    loadingPreview.value = false
  }
}

async function create() {
  creating.value = true
  const key = { subject: 'code', region: 'region', sector: 'sector', risk_type: 'risk_type', periodic: '' }[type.value] as string
  try {
    const rep = await reportsApi.create(type.value, key ? { [key]: param.value.trim().toUpperCase() } : {})
    current.value = rep
    router.replace({ query: { id: rep.id } })
    ui.toast(`${rep.meta.number} hisobot yaratildi`, 'success')
    loadList()
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Hisobot yaratib bo‘lmadi', 'error')
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  await loadList()
  const id = Number(route.query.id)
  if (id) open(id)
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Hisobotlar</h1>
        <p class="page-sub">Har bir hisobotda raqam, sana, ma’lumot davri, model va ma’lumot versiyasi hamda muallif ko‘rsatiladi.</p>
      </div>
    </div>

    <div class="rep-grid">
      <aside class="stack">
        <div class="card card-pad form">
          <div class="card-title">Yangi hisobot</div>
          <label class="field">
            <span class="field-label">Hisobot turi</span>
            <select v-model="type" class="select">
              <option v-for="t in TYPES" :key="t.key" :value="t.key">{{ t.label }}</option>
            </select>
          </label>
          <label v-if="type === 'subject'" class="field">
            <span class="field-label">Ichki kod</span>
            <input v-model="param" class="input" placeholder="SUB-000125" />
          </label>
          <label v-else-if="paramOptions.length" class="field">
            <span class="field-label">Parametr</span>
            <select v-model="param" class="select">
              <option v-for="o in paramOptions" :key="o.v" :value="o.v">{{ o.l }}</option>
            </select>
          </label>
          <p v-else class="xs muted">Joriy tahlil davri bo‘yicha umumiy hisobot.</p>
          <button class="btn btn-primary" :disabled="creating" @click="create"><FilePlus2 :size="15" /> {{ creating ? 'Yaratilmoqda…' : 'Hisobot yaratish' }}</button>
        </div>

        <div class="card">
          <div class="card-head"><div class="card-title">Yaratilgan hisobotlar</div></div>
          <div class="card-body hist">
            <StateBlock v-if="!list.length" kind="empty" compact message="Hali hisobot yaratilmagan." />
            <button v-for="r in list" :key="r.id" class="hist-item" :class="{ active: current?.id === r.id }" @click="open(r.id); router.replace({ query: { id: r.id } })">
              <span class="num hist-no">{{ r.number }}</span>
              <span class="hist-title">{{ r.title }}</span>
              <span class="xs muted">{{ dateTime(r.created_at) }} · {{ r.created_by }}</span>
            </button>
          </div>
        </div>
      </aside>

      <section>
        <div v-if="loadingPreview" class="card card-pad"><LoadingSkeleton :lines="12" /></div>
        <ReportPreview v-else-if="current" :report="current" />
        <div v-else class="card"><StateBlock kind="empty" title="Hisobot tanlanmagan" message="Chapdan yangi hisobot yarating yoki mavjudini tanlang." /></div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.rep-grid { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: var(--gap); align-items: start; }
.form { display: flex; flex-direction: column; gap: 12px; }
.hist { display: flex; flex-direction: column; gap: 4px; max-height: 480px; overflow: auto; }
.hist-item { display: flex; flex-direction: column; gap: 2px; padding: 9px 10px; border: 1px solid transparent; border-radius: 9px; background: transparent; text-align: left; cursor: pointer; }
.hist-item:hover { background: var(--surface-3); }
.hist-item.active { border-color: var(--blue-100); background: var(--blue-50); }
.hist-no { font-size: var(--fs-xs); font-weight: 650; color: var(--blue-600); }
.hist-title { font-size: var(--fs-md); font-weight: 580; color: var(--navy); }
</style>
