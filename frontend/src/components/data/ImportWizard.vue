<script setup lang="ts">
// Import ustasi (prompt §23): 7 bosqich.
import { CheckCircle2, FileUp, Loader2 } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref } from 'vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { dataApi } from '@/services/api'
import { ApiError } from '@/services/http'
import type { DataSource, ImportJob, Job } from '@/types/api'
import { num } from '@/utils/format'
import { JOB_STATUS_LABEL } from '@/utils/labels'

const props = defineProps<{ sources: DataSource[] }>()
const emit = defineEmits<{ done: [] }>()

const STEPS = ['Fayl tanlash', 'Tuzilmani tekshirish', 'Ustunlarni moslashtirish', 'Ma’lumot sifatini tekshirish', 'Takroriy yozuvlarni aniqlash', 'Import tasdig‘i', 'Natija']
const step = ref(0)
const file = ref<File | null>(null)
const sourceId = ref<number | null>(props.sources.find((s) => s.code === 'synthetic_demo_transactions_v1')?.id ?? null)
const job = ref<ImportJob | null>(null)
const mapping = ref<Record<string, string | null>>({})
const busy = ref(false)
const error = ref<string | null>(null)
const task = ref<Job | null>(null)
const dragging = ref(false)
let poll: ReturnType<typeof setInterval> | undefined

const DIM_LABEL: Record<string, string> = {
  completeness: 'To‘liqlik', validity: 'To‘g‘rilik', uniqueness: 'Yagonalik',
  conformity: 'Muvofiqlik', timeliness: 'Dolzarblik', logic: 'Mantiqiy to‘g‘rilik',
}

function pick(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) file.value = f
}
function drop(e: DragEvent) {
  dragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) file.value = f
}

async function run<T>(fn: () => Promise<T>): Promise<T | null> {
  busy.value = true
  error.value = null
  try {
    return await fn()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Kutilmagan xato'
    return null
  } finally {
    busy.value = false
  }
}

async function upload() {
  if (!file.value) return
  const res = await run(() => dataApi.upload(file.value!, sourceId.value))
  if (res) {
    job.value = res
    mapping.value = { ...res.mapping }
    step.value = 1
  }
}

async function saveMapping() {
  const res = await run(() => dataApi.setMapping(job.value!.id, mapping.value))
  if (!res) return
  const v = await run(() => dataApi.validate(job.value!.id))
  if (v) {
    job.value = v
    step.value = 3
  }
}

async function confirm() {
  const res = await run(() => dataApi.confirm(job.value!.id))
  if (!res) return
  task.value = res.job
  step.value = 6
  poll = setInterval(async () => {
    task.value = await dataApi.job(res.job.id).catch(() => task.value)
    if (task.value && ['COMPLETED', 'FAILED'].includes(task.value.status)) {
      clearInterval(poll)
      job.value = await dataApi.getImport(job.value!.id).catch(() => job.value)
      emit('done')
    }
  }, 700)
}

function restart() {
  clearInterval(poll)
  step.value = 0
  file.value = null
  job.value = null
  task.value = null
  error.value = null
}

const requiredMissing = computed(() =>
  job.value ? Object.entries(job.value.target_fields).filter(([k, v]) => v.required && !mapping.value[k]).map(([, v]) => v.label) : [],
)
onBeforeUnmount(() => clearInterval(poll))
</script>

<template>
  <div class="wiz">
    <ol class="steps">
      <li v-for="(s, i) in STEPS" :key="s" :class="{ done: i < step, cur: i === step }">
        <span class="num">{{ i < step ? '✓' : i + 1 }}</span>{{ s }}
      </li>
    </ol>

    <div v-if="error" class="notice notice-danger" role="alert">{{ error }}</div>

    <!-- 1 -->
    <div v-if="step === 0" class="pane">
      <label class="drop" :class="{ over: dragging }" @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="drop">
        <FileUp :size="26" />
        <b>{{ file ? file.name : 'Faylni shu yerga tashlang yoki tanlang' }}</b>
        <span class="xs muted">{{ file ? `${num(file.size / 1024, 1)} KB` : 'CSV, XLSX yoki JSON · 10 MB gacha' }}</span>
        <input type="file" accept=".csv,.xlsx,.json" class="sr-only" @change="pick" />
      </label>
      <label class="field">
        <span class="field-label">Ma’lumot manbasi</span>
        <select v-model="sourceId" class="select">
          <option :value="null">Ko‘rsatilmagan</option>
          <option v-for="s in sources" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </label>
      <p class="xs muted">Namuna fayllar: <code>data/samples/</code> (sintetik, qasddan qo‘yilgan xatolar bilan).</p>
      <div class="actions"><button class="btn btn-primary" :disabled="!file || busy" @click="upload">{{ busy ? 'Yuklanmoqda…' : 'Yuklash va tekshirish' }}</button></div>
    </div>

    <!-- 2 -->
    <div v-else-if="step === 1 && job" class="pane">
      <div class="notice notice-info"><CheckCircle2 :size="16" /> Fayl o‘qildi: {{ num(job.total_rows) }} qator, {{ job.columns.length }} ustun ({{ job.format.toUpperCase() }}).</div>
      <div class="table-wrap preview">
        <table class="table">
          <thead><tr><th v-for="c in job.columns" :key="c">{{ c }}</th></tr></thead>
          <tbody><tr v-for="(r, i) in job.preview" :key="i"><td v-for="c in job.columns" :key="c" class="small">{{ r[c] ?? '—' }}</td></tr></tbody>
        </table>
      </div>
      <div class="actions"><button class="btn" @click="restart">Boshqa fayl</button><button class="btn btn-primary" @click="step = 2">Davom etish</button></div>
    </div>

    <!-- 3 -->
    <div v-else-if="step === 2 && job" class="pane">
      <p class="small muted">Fayl ustunlarini RASAD maydonlariga moslashtiring. Tavsiyalar ustun nomlari asosida avtomatik tanlangan.</p>
      <div class="map-grid">
        <template v-for="(spec, key) in job.target_fields" :key="key">
          <span class="map-target">{{ spec.label }} <span v-if="spec.required" class="req">*</span></span>
          <select v-model="mapping[key]" class="select">
            <option :value="null">— moslashtirilmagan —</option>
            <option v-for="c in job.columns" :key="c" :value="c">{{ c }}</option>
          </select>
        </template>
      </div>
      <div v-if="requiredMissing.length" class="notice notice-warn">Majburiy maydonlar: {{ requiredMissing.join(', ') }}</div>
      <div class="actions"><button class="btn" @click="step = 1">Orqaga</button><button class="btn btn-primary" :disabled="!!requiredMissing.length || busy" @click="saveMapping">{{ busy ? 'Tekshirilmoqda…' : 'Sifatni tekshirish' }}</button></div>
    </div>

    <!-- 4 -->
    <div v-else-if="step === 3 && job" class="pane">
      <div class="dq-top">
        <div><span class="xs muted">Sifat bahosi</span><b class="num big">{{ num(job.dq.score, 1) }}<small>/100</small></b></div>
        <div><span class="xs muted">Tanilgan subyektlar</span><b class="num">{{ num(job.dq.matched_subjects) }}</b></div>
        <div><span class="xs muted">Noma’lum STIR</span><b class="num">{{ num(job.dq.unknown_stir) }}</b></div>
      </div>
      <div class="dims">
        <div v-for="(v, k) in job.dq.dimensions" :key="k" class="dim"><span>{{ DIM_LABEL[k] ?? k }}</span><i><em :style="{ width: `${v}%` }" :class="{ warn: v < 60 }" /></i><b class="num">{{ num(v, 0) }}</b></div>
      </div>
      <div v-if="job.errors.length" class="errs">
        <div class="section-label">Tekshiruv xatolari ({{ job.errors.length }})</div>
        <ul><li v-for="e in job.errors.slice(0, 30)" :key="e.row"><b class="num">{{ e.row }}-qator:</b> {{ e.messages.join('; ') }}</li></ul>
      </div>
      <div class="actions"><button class="btn" @click="step = 2">Orqaga</button><button class="btn btn-primary" @click="step = 4">Davom etish</button></div>
    </div>

    <!-- 5 -->
    <div v-else-if="step === 4 && job" class="pane">
      <div class="counts">
        <div class="cnt ok"><span>Qabul qilinadi</span><b class="num">{{ num(job.accepted) }}</b></div>
        <div class="cnt bad"><span>Rad etiladi</span><b class="num">{{ num(job.rejected) }}</b></div>
        <div class="cnt dup"><span>Takroriy yozuvlar</span><b class="num">{{ num(job.duplicates) }}</b></div>
      </div>
      <p class="small muted">To‘liq bir xil qatorlar takroriy hisoblanadi va bir marta olinadi. Xatoli qatorlar rad etiladi.</p>
      <div class="actions"><button class="btn" @click="step = 3">Orqaga</button><button class="btn btn-primary" @click="step = 5">Davom etish</button></div>
    </div>

    <!-- 6 -->
    <div v-else-if="step === 5 && job" class="pane">
      <div class="notice">
        <span><b>{{ job.filename }}</b>: {{ num(job.accepted) }} ta qator RAW qatlamiga yuklanadi. Rad etilgan: {{ num(job.rejected) }}, takroriy: {{ num(job.duplicates) }}.
        Tahlilga qo‘shish keyingi qayta hisoblashda amalga oshiriladi. Amal audit jurnaliga yoziladi.</span>
      </div>
      <div class="actions"><button class="btn" @click="step = 4">Orqaga</button><button class="btn btn-primary" :disabled="busy" @click="confirm">Importni tasdiqlash</button></div>
    </div>

    <!-- 7 -->
    <div v-else-if="step === 6" class="pane">
      <div v-if="task && !['COMPLETED', 'FAILED'].includes(task.status)" class="notice notice-info"><Loader2 :size="16" class="spin" /> Fon vazifasi: {{ JOB_STATUS_LABEL[task.status] }}…</div>
      <StateBlock v-else-if="task?.status === 'FAILED'" kind="import-error" :message="task.error ?? undefined" />
      <template v-else-if="task && job">
        <div class="notice notice-info"><CheckCircle2 :size="16" /> Import yakunlandi (vazifa #{{ task.id }}).</div>
        <div class="counts">
          <div class="cnt ok"><span>Qabul qilindi</span><b class="num">{{ num(Number(task.result.accepted)) }}</b></div>
          <div class="cnt bad"><span>Rad etildi</span><b class="num">{{ num(Number(task.result.rejected)) }}</b></div>
          <div class="cnt dup"><span>Takroriy</span><b class="num">{{ num(Number(task.result.duplicates)) }}</b></div>
        </div>
        <p class="xs muted">RAW fayl: {{ task.result.raw_file }}</p>
      </template>
      <div class="actions"><button class="btn btn-primary" @click="restart">Yangi import</button></div>
    </div>
  </div>
</template>

<style scoped>
.wiz { display: flex; flex-direction: column; gap: 14px; }
.steps { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin: 0; padding: 0; list-style: none; }
.steps li { display: flex; flex-direction: column; gap: 6px; padding: 8px 9px; border-top: 3px solid var(--border); font-size: var(--fs-xs); color: var(--muted); font-weight: 560; }
.steps li span { display: grid; place-items: center; width: 20px; height: 20px; border-radius: 50%; background: var(--surface-3); color: var(--muted); font-size: 11px; }
.steps li.done { border-color: var(--navy-3); color: var(--text-2); }
.steps li.done span { background: var(--navy-3); color: #fff; }
.steps li.cur { border-color: var(--blue); color: var(--navy); }
.steps li.cur span { background: var(--blue); color: #fff; }
.pane { display: flex; flex-direction: column; gap: 12px; }
.drop { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 32px; border: 2px dashed var(--border-strong); border-radius: 12px; background: var(--surface-2); color: var(--muted); cursor: pointer; text-align: center; transition: all var(--t-fast); }
.drop b { color: var(--navy); }
.drop.over, .drop:hover { border-color: var(--blue); background: var(--blue-50); }
.actions { display: flex; justify-content: flex-end; gap: 8px; }
.preview { max-height: 260px; border: 1px solid var(--border); border-radius: 8px; }
.map-grid { display: grid; grid-template-columns: 220px 1fr; gap: 8px 14px; align-items: center; }
.map-target { font-size: var(--fs-md); font-weight: 560; }
.req { color: var(--risk-high); }
.dq-top { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.dq-top div { display: flex; flex-direction: column; padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; }
.dq-top b { font-size: 20px; color: var(--navy); }
.dq-top .big { font-size: 26px; }
.dq-top small { font-size: 13px; color: var(--muted); }
.dims { display: flex; flex-direction: column; gap: 6px; }
.dim { display: grid; grid-template-columns: 150px 1fr 34px; gap: 10px; align-items: center; font-size: var(--fs-sm); }
.dim i { height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.dim em { display: block; height: 100%; background: var(--navy-3); }
.dim em.warn { background: var(--risk-medium); }
.dim b { text-align: right; }
.errs ul { margin: 6px 0 0; padding-left: 18px; max-height: 180px; overflow: auto; font-size: var(--fs-sm); color: var(--text-2); }
.counts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.cnt { display: flex; flex-direction: column; padding: 12px 14px; border-radius: 10px; border: 1px solid var(--border); }
.cnt b { font-size: 24px; color: var(--navy); }
.cnt span { font-size: var(--fs-sm); color: var(--muted); }
.cnt.ok { border-left: 4px solid var(--risk-low); }
.cnt.bad { border-left: 4px solid var(--risk-high); }
.cnt.dup { border-left: 4px solid var(--muted-2); }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
