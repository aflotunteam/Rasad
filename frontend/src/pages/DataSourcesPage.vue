<script setup lang="ts">
import { AlertCircle, CheckCircle2, Clock, PowerOff, Route } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import CalibrationPanel from '@/components/data/CalibrationPanel.vue'
import ImportWizard from '@/components/data/ImportWizard.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import UiDrawer from '@/components/ui/UiDrawer.vue'
import { dataApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import type { DataSource, ImportJob, Job } from '@/types/api'
import { dateTime, num, relative } from '@/utils/format'
import { JOB_STATUS_LABEL, SOURCE_STATUS_LABEL, SOURCE_TYPE_LABEL } from '@/utils/labels'

const auth = useAuthStore()
const sources = ref<DataSource[] | null>(null)
const imports = ref<ImportJob[]>([])
const jobs = ref<Job[]>([])
const error = ref(false)
const lineageFor = ref<DataSource | null>(null)
const lineage = ref<Record<string, string>[]>([])
const STATUS_ICON = { active: CheckCircle2, delayed: Clock, error: AlertCircle, disabled: PowerOff }

async function load() {
  error.value = false
  try {
    sources.value = await dataApi.sources()
    if (auth.can('imports')) imports.value = await dataApi.imports()
    jobs.value = await dataApi.jobs().catch(() => [])
  } catch {
    error.value = true
  }
}

async function openLineage(s: DataSource) {
  lineageFor.value = s
  lineage.value = await dataApi.lineage(s.id).catch(() => [])
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Ma’lumot manbalari</h1>
        <p class="page-sub">Manbalar holati, yuklash sifati va ma’lumot kelib chiqishi (lineage). Barcha manbalar sintetik.</p>
      </div>
    </div>

    <StateBlock v-if="error" kind="server-error" class="card" @retry="load" />
    <div v-else-if="!sources" class="card card-pad"><LoadingSkeleton :lines="6" /></div>
    <template v-else>
      <section class="src-grid">
        <article v-for="s in sources" :key="s.id" class="card src" :class="`src-${s.status}`">
          <div class="row">
            <span class="src-status"><component :is="STATUS_ICON[s.status]" :size="14" /> {{ SOURCE_STATUS_LABEL[s.status] }}</span>
            <span class="spacer" />
            <span class="chip">{{ SOURCE_TYPE_LABEL[s.type] ?? s.type }}</span>
          </div>
          <h3 class="src-name">{{ s.name }}</h3>
          <code class="xs muted">{{ s.code }}</code>
          <p class="small muted">{{ s.description }}</p>
          <dl class="src-stats">
            <div><dt>Oxirgi yuklash</dt><dd :title="dateTime(s.last_load_at)">{{ relative(s.last_load_at) }}</dd></div>
            <div><dt>Qatorlar</dt><dd class="num">{{ num(s.rows) }}</dd></div>
            <div><dt>Rad etilgan</dt><dd class="num">{{ num(s.rejected) }}</dd></div>
            <div><dt>Sifat bahosi</dt><dd class="num">{{ s.quality_score === null ? 'Ma’lumot mavjud emas' : `${num(s.quality_score, 1)}/100` }}</dd></div>
          </dl>
          <div v-if="s.last_error" class="notice notice-danger xs">{{ s.last_error }}</div>
          <button class="btn btn-sm lin" @click="openLineage(s)"><Route :size="14" /> Ma’lumot kelib chiqishi</button>
        </article>
      </section>

      <CalibrationPanel />

      <section v-if="auth.can('imports')" class="card imp">
        <div class="card-head"><div><div class="card-title">Ma’lumot importi</div><div class="card-sub">CSV, XLSX yoki JSON faylni tekshirib, RAW qatlamiga yuklash</div></div></div>
        <div class="card-body"><ImportWizard :sources="sources" @done="load" /></div>
      </section>

      <section class="two">
        <div v-if="auth.can('imports')" class="card">
          <div class="card-head"><div class="card-title">Importlar tarixi</div></div>
          <StateBlock v-if="!imports.length" kind="empty" compact message="Hali import qilinmagan." />
          <table v-else class="table">
            <thead><tr><th>Fayl</th><th>Bosqich</th><th class="right">Qabul</th><th class="right">Rad</th><th class="right">Takror</th><th>Vaqt</th></tr></thead>
            <tbody>
              <tr v-for="i in imports" :key="i.id">
                <td class="small">{{ i.filename }}</td><td class="small">{{ i.stage === 'done' ? 'Yakunlangan' : i.stage }}</td>
                <td class="right num">{{ num(i.accepted) }}</td><td class="right num">{{ num(i.rejected) }}</td><td class="right num">{{ num(i.duplicates) }}</td>
                <td class="small muted">{{ relative(i.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="card">
          <div class="card-head"><div><div class="card-title">Fon vazifalar</div><div class="card-sub">QUEUED → RUNNING → COMPLETED / FAILED</div></div></div>
          <StateBlock v-if="!jobs.length" kind="empty" compact message="Fon vazifalar hali ishga tushirilmagan." />
          <table v-else class="table">
            <thead><tr><th>#</th><th>Turi</th><th>Holat</th><th>Boshlangan</th><th>Tugagan</th></tr></thead>
            <tbody>
              <tr v-for="j in jobs" :key="j.id">
                <td class="num">{{ j.id }}</td><td class="small">{{ j.type === 'import' ? 'Import' : 'Qayta hisoblash' }}</td>
                <td class="small">{{ JOB_STATUS_LABEL[j.status] }}</td>
                <td class="small muted">{{ dateTime(j.started_at) }}</td><td class="small muted">{{ dateTime(j.finished_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <UiDrawer :open="!!lineageFor" :title="lineageFor?.name ?? ''" subtitle="Ma’lumot kelib chiqishi: qayerdan, qachon, qanday o‘zgartirildi" @close="lineageFor = null">
      <StateBlock v-if="!lineage.length" kind="empty" compact />
      <ol v-else class="lin-list">
        <li v-for="l in lineage" :key="l.id">
          <b>{{ l.transformation }}</b> → <code>{{ l.target_table }}</code>
          <div class="xs muted">{{ l.source_record_id }} · {{ dateTime(l.processed_at) }} · {{ l.pipeline_version }}</div>
        </li>
      </ol>
    </UiDrawer>
  </div>
</template>

<style scoped>
.src-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: var(--gap); margin-bottom: var(--gap); }
.src { display: flex; flex-direction: column; gap: 8px; padding: 16px 18px; border-top: 3px solid var(--risk-low); }
.src-delayed { border-top-color: var(--risk-medium); }
.src-error { border-top-color: var(--risk-high); }
.src-disabled { border-top-color: var(--muted-2); }
.src-status { display: inline-flex; align-items: center; gap: 5px; font-size: var(--fs-sm); font-weight: 600; color: var(--risk-low-text); }
.src-delayed .src-status { color: var(--risk-medium-text); }
.src-error .src-status { color: var(--risk-high); }
.src-name { font-size: var(--fs-lg); }
.src-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; margin: 4px 0 0; }
.src-stats dt { font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
.src-stats dd { margin: 1px 0 0; font-weight: 600; font-size: var(--fs-md); }
.lin { align-self: flex-start; margin-top: auto; }
.imp { margin-bottom: var(--gap); }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap); }
.lin-list { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 10px; font-size: var(--fs-md); }
</style>
