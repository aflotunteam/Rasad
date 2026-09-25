<script setup lang="ts">
import { ExternalLink, UserPlus } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import RiskBadge from '@/components/risk/RiskBadge.vue'
import RiskTypeTag from '@/components/risk/RiskTypeTag.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import UiPagination from '@/components/ui/UiPagination.vue'
import { alertsApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { useUiStore } from '@/stores/ui'
import type { AlertPage, AlertStatus } from '@/types/api'
import { dateTime, num, relative } from '@/utils/format'
import { ALERT_STATUS_LABEL } from '@/utils/labels'

const router = useRouter()
const auth = useAuthStore()
const meta = useMetaStore()
const ui = useUiStore()

const f = reactive({ status: 'new', severity: '', region: '', risk_type: '', q: '' })
const page = ref(1)
const pageSize = ref(25)
const data = ref<AlertPage | null>(null)
const loading = ref(false)
const error = ref(false)
const selected = ref<Set<number>>(new Set())
const analysts = ref<{ id: number; full_name: string }[]>([])
const bulkStatus = ref<AlertStatus | ''>('')
const bulkAnalyst = ref<number | ''>('')
const canWrite = computed(() => auth.can('alerts.write'))
const STATUSES = Object.keys(ALERT_STATUS_LABEL) as AlertStatus[]

async function load() {
  loading.value = true
  error.value = false
  try {
    data.value = await alertsApi.list({ ...f, page: page.value, page_size: pageSize.value })
    selected.value = new Set()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

watch(f, () => {
  page.value = 1
  load()
})
watch([page, pageSize], load)

const allChecked = computed(() => !!data.value?.items.length && data.value.items.every((a) => selected.value.has(a.id)))
function toggleAll() {
  selected.value = allChecked.value ? new Set() : new Set(data.value?.items.map((a) => a.id))
}
function toggle(id: number) {
  const s = new Set(selected.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selected.value = s
}

async function apply(patch: { status?: AlertStatus; analyst_id?: number }) {
  if (!selected.value.size) return
  try {
    const res = await alertsApi.update([...selected.value], patch)
    ui.toast(`${res.updated} ta ogohlantirish yangilandi`, 'success')
    window.dispatchEvent(new Event('rasad:alerts-changed'))
    bulkStatus.value = ''
    bulkAnalyst.value = ''
    load()
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'O‘zgartirib bo‘lmadi', 'error')
  }
}

onMounted(async () => {
  if (auth.regionScope) f.region = auth.regionScope
  load()
  if (canWrite.value) analysts.value = await alertsApi.analysts().catch(() => [])
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Ogohlantirishlar</h1>
        <p class="page-sub">Xavf bahosi yuqori chegaraga yaqin yoki undan oshgan holatlar. Mas’ul biriktiring va holatni yuriting.</p>
      </div>
    </div>

    <div class="status-tabs" role="tablist">
      <button role="tab" :aria-selected="f.status === ''" class="stab" :class="{ active: f.status === '' }" @click="f.status = ''">
        Barchasi <span class="num">{{ num(Object.values(data?.counts ?? {}).reduce((a, b) => a + (b ?? 0), 0)) }}</span>
      </button>
      <button v-for="s in STATUSES" :key="s" role="tab" :aria-selected="f.status === s" class="stab" :class="{ active: f.status === s }" @click="f.status = s">
        {{ ALERT_STATUS_LABEL[s] }} <span class="num">{{ num(data?.counts[s] ?? 0) }}</span>
      </button>
    </div>

    <div class="card">
      <div class="filters">
        <input v-model="f.q" class="input" placeholder="Subyekt yoki ogohlantirish kodi" aria-label="Qidirish" />
        <select v-model="f.severity" class="select" aria-label="Daraja">
          <option value="">Har qanday daraja</option>
          <option value="high">Yuqori</option>
          <option value="medium">O‘rta</option>
        </select>
        <select v-model="f.region" class="select" aria-label="Hudud" :disabled="!!auth.regionScope">
          <option value="">Barcha hududlar</option>
          <option v-for="r in meta.meta?.regions" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
        <select v-model="f.risk_type" class="select" aria-label="Xavf turi">
          <option value="">Har qanday xavf turi</option>
          <option v-for="t in meta.meta?.risk_types" :key="t.code" :value="t.code">{{ t.code }} — {{ t.name }}</option>
        </select>
      </div>

      <div v-if="canWrite" class="bulk" :class="{ on: selected.size }">
        <span class="small"><b class="num">{{ selected.size }}</b> ta tanlandi</span>
        <select v-model="bulkStatus" class="select" :disabled="!selected.size" aria-label="Yangi holat">
          <option value="">Holatni o‘zgartirish…</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ ALERT_STATUS_LABEL[s] }}</option>
        </select>
        <button class="btn btn-sm" :disabled="!selected.size || !bulkStatus" @click="apply({ status: bulkStatus as AlertStatus })">Qo‘llash</button>
        <select v-model="bulkAnalyst" class="select" :disabled="!selected.size" aria-label="Mas’ul xodim">
          <option value="">Mas’ul biriktirish…</option>
          <option v-for="a in analysts" :key="a.id" :value="a.id">{{ a.full_name }}</option>
        </select>
        <button class="btn btn-sm" :disabled="!selected.size || !bulkAnalyst" @click="apply({ analyst_id: Number(bulkAnalyst) })"><UserPlus :size="14" /> Biriktirish</button>
      </div>

      <StateBlock v-if="error" kind="server-error" @retry="load" />
      <div v-else-if="!data" class="card-pad"><LoadingSkeleton :lines="8" :height="22" /></div>
      <StateBlock v-else-if="!data.items.length" kind="empty" message="Tanlangan holat bo‘yicha ogohlantirish yo‘q." />
      <div v-else class="table-wrap" :class="{ dim: loading }">
        <table class="table">
          <thead>
            <tr>
              <th v-if="canWrite" style="width: 36px"><input type="checkbox" :checked="allChecked" aria-label="Barchasini tanlash" @change="toggleAll" /></th>
              <th>Kod</th>
              <th>Daraja</th>
              <th>Subyekt</th>
              <th>Xavf turi</th>
              <th>Hudud</th>
              <th>Aniqlangan</th>
              <th>Mas’ul</th>
              <th>Holat</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in data.items" :key="a.id" :class="{ sel: selected.has(a.id) }">
              <td v-if="canWrite"><input type="checkbox" :checked="selected.has(a.id)" :aria-label="`${a.code} ni tanlash`" @change="toggle(a.id)" /></td>
              <td class="num small muted">{{ a.code }}</td>
              <td><RiskBadge :level="a.severity" :score="a.score" size="sm" /></td>
              <td><span class="code">{{ a.subject_code }}</span><div class="xs muted">{{ meta.sectorName(a.sector_id) }}</div></td>
              <td><RiskTypeTag :code="a.risk_type" /></td>
              <td>{{ meta.regionShort(a.region_id) }}</td>
              <td class="small" :title="dateTime(a.detected_at)">{{ relative(a.detected_at) }}</td>
              <td class="small">{{ a.analyst?.full_name ?? '—' }}</td>
              <td><span class="st" :class="`st-${a.status}`">{{ ALERT_STATUS_LABEL[a.status] }}</span></td>
              <td><button class="btn btn-sm btn-ghost" @click="router.push({ name: 'subject', params: { code: a.subject_code } })"><ExternalLink :size="14" /> Ochish</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <UiPagination v-if="data?.total" v-model:page="page" v-model:page-size="pageSize" :total="data.total" :sizes="[25, 50, 100]" />
    </div>
  </div>
</template>

<style scoped>
.status-tabs { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }
.stab { display: inline-flex; align-items: center; gap: 8px; height: 34px; padding: 0 14px; border: 1px solid var(--border); border-radius: 999px; background: #fff; color: var(--text-2); font-weight: 560; font-size: var(--fs-md); cursor: pointer; }
.stab span { padding: 1px 7px; border-radius: 999px; background: var(--surface-3); font-size: var(--fs-xs); }
.stab.active { background: var(--navy); border-color: var(--navy); color: #fff; }
.stab.active span { background: rgba(255, 255, 255, 0.15); }
.filters { display: grid; grid-template-columns: 1.4fr repeat(3, 1fr); gap: 10px; padding: 14px 16px; border-bottom: 1px solid var(--border); }
.filters .input, .filters .select { height: 34px; font-size: var(--fs-sm); }
.bulk { display: flex; align-items: center; gap: 8px; padding: 10px 16px; border-bottom: 1px solid var(--border); background: var(--surface-2); }
.bulk.on { background: var(--blue-50); }
.bulk .select { width: 220px; height: 30px; font-size: var(--fs-sm); }
.table-wrap.dim { opacity: 0.6; }
tr.sel { background: #f1f6ff; }
.st { display: inline-flex; padding: 2px 9px; border-radius: 999px; font-size: var(--fs-xs); font-weight: 600; background: var(--surface-3); color: var(--text-2); }
.st-new { background: var(--blue-50); color: var(--blue-600); }
.st-in_review { background: #eef2f8; color: var(--navy); }
.st-confirmed { background: var(--navy); color: #fff; }
.st-closed { color: var(--muted); }
</style>
