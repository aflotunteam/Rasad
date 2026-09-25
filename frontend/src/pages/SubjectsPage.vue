<script setup lang="ts">
import { ArrowDown, ArrowUp, ArrowUpDown, Columns3, Download } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ConfidenceBadge from '@/components/risk/ConfidenceBadge.vue'
import DataQualityBadge from '@/components/risk/DataQualityBadge.vue'
import ExpertStatusTag from '@/components/risk/ExpertStatusTag.vue'
import RiskBadge from '@/components/risk/RiskBadge.vue'
import RiskTypeTag from '@/components/risk/RiskTypeTag.vue'
import SubjectFilters, { type Filters } from '@/components/subjects/SubjectFilters.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import SyntheticBadge from '@/components/ui/SyntheticBadge.vue'
import UiPagination from '@/components/ui/UiPagination.vue'
import { subjectsApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { useUiStore } from '@/stores/ui'
import type { Page, SubjectRow } from '@/types/api'
import { date, num } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()
const auth = useAuthStore()
const ui = useUiStore()

const EMPTY: Filters = { region: '', sector: '', level: '', risk_type: '', expert_status: '', dq: '', confidence: '', q: '' }
const KEYS = Object.keys(EMPTY) as (keyof Filters)[]

function fromQuery(): Filters {
  const f = { ...EMPTY }
  for (const k of KEYS) if (typeof route.query[k] === 'string') f[k] = route.query[k] as string
  if (auth.regionScope) f.region = auth.regionScope
  return f
}

const filters = ref<Filters>(fromQuery())
const sort = reactive({ field: (route.query.sort as string) || 'score', order: ((route.query.order as string) || 'desc') as 'asc' | 'desc' })
const page = ref(Number(route.query.page) || 1)
const pageSize = ref(25)
const data = ref<Page<SubjectRow> | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const COLUMNS = [
  { key: 'code', label: 'Ichki kod', sortable: true, fixed: true },
  { key: 'region', label: 'Hudud', sortable: true },
  { key: 'sector', label: 'Faoliyat turi', sortable: true },
  { key: 'score', label: 'Xavf bahosi', sortable: true },
  { key: 'confidence', label: 'Ishonch', sortable: true },
  { key: 'risk_type', label: 'Asosiy xavf turi', sortable: false },
  { key: 'dq_score', label: 'Ma’lumot sifati', sortable: true },
  { key: 'expert_status', label: 'Ekspert holati', sortable: false },
  { key: 'computed_at', label: 'Oxirgi tahlil', sortable: true },
] as const
type ColKey = (typeof COLUMNS)[number]['key']

const COLS_KEY = 'rasad.subject-columns'
function readCols(): ColKey[] {
  try {
    const v = JSON.parse(localStorage.getItem(COLS_KEY) ?? 'null')
    if (Array.isArray(v)) return v
  } catch {
    /* sukut bo'yicha barcha ustunlar */
  }
  return COLUMNS.map((c) => c.key)
}
const visibleCols = ref<ColKey[]>(readCols())
const colMenu = ref(false)
const shown = computed(() => COLUMNS.filter((c) => visibleCols.value.includes(c.key)))

function toggleCol(key: ColKey) {
  visibleCols.value = visibleCols.value.includes(key) ? visibleCols.value.filter((k) => k !== key) : [...visibleCols.value, key]
  try {
    localStorage.setItem(COLS_KEY, JSON.stringify(visibleCols.value))
  } catch {
    /* e'tiborsiz */
  }
}

const query = computed(() => ({ ...filters.value, sort: sort.field, order: sort.order, page: page.value, page_size: pageSize.value }))

let seq = 0
async function load() {
  const my = ++seq
  loading.value = true
  error.value = null
  try {
    const res = await subjectsApi.list(query.value)
    if (my === seq) data.value = res
  } catch (e) {
    if (my === seq) error.value = e instanceof ApiError ? e.message : 'Server xatosi'
  } finally {
    if (my === seq) loading.value = false
  }
}

let qTimer: ReturnType<typeof setTimeout> | undefined
watch(
  filters,
  (f, old) => {
    page.value = 1
    clearTimeout(qTimer)
    qTimer = setTimeout(load, f.q !== old?.q ? 280 : 0)
  },
  { deep: true },
)
watch([page, pageSize], load)
watch(query, (q) => {
  const clean = Object.fromEntries(Object.entries(q).filter(([k, v]) => v !== '' && !(k === 'page_size') && !(k === 'page' && v === 1)))
  router.replace({ query: clean })
})

function sortBy(field: string) {
  if (sort.field === field) sort.order = sort.order === 'desc' ? 'asc' : 'desc'
  else {
    sort.field = field
    sort.order = field === 'code' || field === 'region' || field === 'sector' ? 'asc' : 'desc'
  }
  page.value = 1
  load()
}

function reset() {
  filters.value = { ...EMPTY, region: auth.regionScope ?? '' }
}

async function exportCsv() {
  try {
    await subjectsApi.exportCsv(query.value)
    ui.toast('Ro‘yxat CSV faylga eksport qilindi', 'success')
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Eksport qilib bo‘lmadi', 'error')
  }
}

function open(code: string) {
  router.push({ name: 'subject', params: { code } })
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Subyektlar</h1>
        <p class="page-sub">Xavf bahosi, ishonch darajasi va ma’lumot sifati alohida ko‘rsatiladi. Qatorni bosib subyekt kartasini oching.</p>
      </div>
      <div class="row">
        <SyntheticBadge compact />
        <div class="col-menu" @focusout="(e) => !(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node) && (colMenu = false)">
          <button class="btn btn-sm" :aria-expanded="colMenu" @click="colMenu = !colMenu"><Columns3 :size="14" /> Ustunlar</button>
          <div v-if="colMenu" class="col-pop card">
            <label v-for="c in COLUMNS" :key="c.key" class="col-opt">
              <input type="checkbox" :checked="visibleCols.includes(c.key)" :disabled="'fixed' in c" @change="toggleCol(c.key)" />
              {{ c.label }}
            </label>
          </div>
        </div>
        <button class="btn btn-sm" @click="exportCsv"><Download :size="14" /> CSV eksport</button>
      </div>
    </div>

    <div class="card">
      <SubjectFilters v-model="filters" @reset="reset" />

      <div class="table-meta">
        <span class="small"><b class="num">{{ num(data?.total ?? 0) }}</b> <span class="muted">ta subyekt</span></span>
        <span class="xs muted">Chegaralar: past &lt; {{ meta.thresholds.low }}, o‘rta {{ meta.thresholds.low }}–{{ meta.thresholds.high - 1 }}, yuqori ≥ {{ meta.thresholds.high }} (MVP uchun sozlanadigan qiymatlar)</span>
      </div>

      <StateBlock v-if="error" kind="server-error" :message="error" @retry="load" />
      <div v-else-if="!data && loading" class="card-pad"><LoadingSkeleton :lines="10" :height="22" /></div>
      <StateBlock v-else-if="data && !data.items.length" kind="empty">
        <button class="btn btn-sm" @click="reset">Filtrlarni tozalash</button>
      </StateBlock>
      <div v-else-if="data" class="table-wrap" :class="{ dim: loading }">
        <table class="table">
          <thead>
            <tr>
              <th v-for="c in shown" :key="c.key" :aria-sort="sort.field === c.key ? (sort.order === 'asc' ? 'ascending' : 'descending') : 'none'">
                <button v-if="c.sortable" class="th-sort" @click="sortBy(c.key)">
                  {{ c.label }}
                  <component :is="sort.field !== c.key ? ArrowUpDown : sort.order === 'asc' ? ArrowUp : ArrowDown" :size="12" />
                </button>
                <span v-else>{{ c.label }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in data.items"
              :key="r.code"
              class="clickable"
              tabindex="0"
              @click="open(r.code)"
              @keydown.enter="open(r.code)"
            >
              <td v-if="visibleCols.includes('code')"><span class="code">{{ r.code }}</span></td>
              <td v-if="visibleCols.includes('region')">{{ meta.regionShort(r.region_id) }}</td>
              <td v-if="visibleCols.includes('sector')">{{ meta.sectorName(r.sector_id) }}</td>
              <td v-if="visibleCols.includes('score')"><RiskBadge :score="r.score" :level="r.level" size="sm" /></td>
              <td v-if="visibleCols.includes('confidence')"><ConfidenceBadge :level="r.confidence" size="sm" /></td>
              <td v-if="visibleCols.includes('risk_type')"><RiskTypeTag :code="r.primary_risk_type" /></td>
              <td v-if="visibleCols.includes('dq_score')"><DataQualityBadge :value="r.dq_score" size="sm" /></td>
              <td v-if="visibleCols.includes('expert_status')"><ExpertStatusTag :status="r.expert_status" /></td>
              <td v-if="visibleCols.includes('computed_at')" class="muted small num">{{ date(r.computed_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <UiPagination
        v-if="data && data.total"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="data.total"
        :sizes="[25, 50, 100]"
      />
    </div>
  </div>
</template>

<style scoped>
.table-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
}

.table-wrap { max-height: calc(100vh - 360px); min-height: 300px; transition: opacity var(--t-fast); }
.table-wrap.dim { opacity: 0.6; }

.th-sort {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  letter-spacing: inherit;
  text-transform: inherit;
  cursor: pointer;
}

.th-sort:hover { color: var(--navy); }
.col-menu { position: relative; }

.col-pop {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 200px;
  padding: 8px;
  box-shadow: var(--shadow-md);
}

.col-opt { display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-radius: 6px; font-size: var(--fs-md); cursor: pointer; }
.col-opt:hover { background: var(--surface-3); }
</style>
