<script setup lang="ts">
import { ArrowLeft, Building2, CalendarRange, Cpu, FileText, KeyRound, MapPin, RefreshCw } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PeerBenchmark from '@/components/charts/PeerBenchmark.vue'
import RelationshipGraph from '@/components/charts/RelationshipGraph.vue'
import TimeSeriesChart from '@/components/charts/TimeSeriesChart.vue'
import ExpertDecisionPanel from '@/components/expert/ExpertDecisionPanel.vue'
import AiExplanation from '@/components/risk/AiExplanation.vue'
import ExplanationDrawer from '@/components/risk/ExplanationDrawer.vue'
import ExpertStatusTag from '@/components/risk/ExpertStatusTag.vue'
import RiskFactorList from '@/components/risk/RiskFactorList.vue'
import RiskScorePanel from '@/components/risk/RiskScorePanel.vue'
import TrustPanels from '@/components/risk/TrustPanels.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import SyntheticBadge from '@/components/ui/SyntheticBadge.vue'
import { reportsApi, subjectsApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { useUiStore } from '@/stores/ui'
import type { Decision, Explanation, Peers, Relations, SubjectDetail, TimeSeries } from '@/types/api'
import { date, dateTime, periodRange } from '@/utils/format'
import { ALERT_STATUS_LABEL, SIZE_LABEL } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()
const auth = useAuthStore()
const ui = useUiStore()

const code = computed(() => String(route.params.code).toUpperCase())
const detail = ref<SubjectDetail | null>(null)
const error = ref<{ kind: 'forbidden' | 'empty' | 'server-error'; message?: string } | null>(null)
const ts = ref<TimeSeries | null>(null)
const tsMetric = ref('turnover')
const peers = ref<Peers | null>(null)
const rel = ref<Relations | null>(null)
const relDepth = ref(2)
const explanation = ref<Explanation | null>(null)
const decisions = ref<Decision[]>([])
const whyOpen = ref(false)
const regenerating = ref(false)
const creatingReport = ref(false)
const loadMs = ref<number | null>(null)

const SECTIONS = [
  { id: 'xavf', label: 'Xavf bahosi' },
  { id: 'sabablar', label: 'Sabablar' },
  { id: 'vaqt', label: 'Vaqt bo‘yicha og‘ish' },
  { id: 'taqqoslash', label: 'Taqqoslash' },
  { id: 'aloqadorlik', label: 'Aloqadorliklar' },
  { id: 'izoh', label: 'SI izohi' },
  { id: 'qaror', label: 'Ekspert qarori' },
]

async function loadTs() {
  ts.value = null
  ts.value = await subjectsApi.timeseries(code.value, tsMetric.value).catch(() => null)
}

async function loadRel() {
  rel.value = await subjectsApi.relations(code.value, relDepth.value).catch(() => null)
}

async function load() {
  const t0 = performance.now()
  error.value = null
  detail.value = null
  try {
    detail.value = await subjectsApi.get(code.value)
    loadMs.value = Math.round(performance.now() - t0)
  } catch (e) {
    if (e instanceof ApiError && e.status === 403) error.value = { kind: 'forbidden', message: e.message }
    else if (e instanceof ApiError && e.status === 404) error.value = { kind: 'empty', message: 'Subyekt topilmadi' }
    else error.value = { kind: 'server-error' }
    return
  }
  // Qolgan bloklar parallel yuklanadi: karta darhol ko'rinadi.
  loadTs()
  loadRel()
  subjectsApi.peers(code.value).then((p) => (peers.value = p)).catch(() => (peers.value = null))
  subjectsApi.explanation(code.value).then((x) => (explanation.value = x)).catch(() => (explanation.value = null))
  subjectsApi.decisions(code.value).then((d) => (decisions.value = d)).catch(() => (decisions.value = []))
}

async function onDecision(d: Decision) {
  decisions.value = [d, ...decisions.value]
  if (detail.value) detail.value = await subjectsApi.get(code.value)
}

async function regenerate() {
  regenerating.value = true
  try {
    explanation.value = await subjectsApi.regenerateExplanation(code.value)
    if (explanation.value.source === 'ai') ui.toast('SI izohi qayta yozildi', 'success')
    else ui.toast(explanation.value.fallback_reason ?? 'Shablon izohi ko‘rsatildi', 'info')
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Izohni qayta yozib bo‘lmadi', 'error')
  } finally {
    regenerating.value = false
  }
}

async function makeReport() {
  creatingReport.value = true
  try {
    const rep = await reportsApi.create('subject', { code: code.value })
    router.push({ name: 'reports', query: { id: rep.id } })
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Hisobot yaratib bo‘lmadi', 'error')
  } finally {
    creatingReport.value = false
  }
}

function jump(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

watch(tsMetric, loadTs)
watch(relDepth, loadRel)
watch(code, load)
onMounted(load)
</script>

<template>
  <div class="page">
    <button class="btn btn-ghost btn-sm back" @click="router.back()"><ArrowLeft :size="15" /> Orqaga</button>

    <div v-if="error" class="card">
      <StateBlock :kind="error.kind" :message="error.message">
        <RouterLink to="/subjects" class="btn btn-sm">Subyektlar ro‘yxatiga qaytish</RouterLink>
      </StateBlock>
    </div>

    <template v-else-if="detail">
      <!-- Sarlavha -->
      <header class="sd-head card">
        <div class="sd-title">
          <div class="row">
            <h1 class="code sd-code">{{ detail.code }}</h1>
            <SyntheticBadge compact />
            <ExpertStatusTag :status="detail.risk.expert_status" />
            <span v-if="detail.alert" class="chip">Ogohlantirish {{ detail.alert.code }} · {{ ALERT_STATUS_LABEL[detail.alert.status] }}</span>
          </div>
          <div class="sd-meta">
            <span><MapPin :size="14" /> {{ detail.region.name }}</span>
            <span><Building2 :size="14" /> {{ detail.sector.name }} · {{ SIZE_LABEL[detail.size_group] }} hajm · {{ detail.org_form }}</span>
            <span><CalendarRange :size="14" /> Tahlil davri: {{ periodRange(detail.risk.period_start, detail.risk.period_end) }}</span>
            <span><RefreshCw :size="14" /> Oxirgi hisob: {{ dateTime(detail.risk.computed_at) }}</span>
            <span><Cpu :size="14" /> Model: {{ detail.risk.model_version }}</span>
            <span :title="detail.stir_masked ? 'Himoyalangan identifikator: sizning rolingiz uchun maskalangan' : 'Sintetik identifikator'">
              <KeyRound :size="14" /> STIR: <span class="num">{{ detail.stir }}</span>
            </span>
          </div>
        </div>
        <div class="sd-actions">
          <button v-if="auth.can('reports')" class="btn btn-primary" :disabled="creatingReport" @click="makeReport">
            <FileText :size="16" /> {{ creatingReport ? 'Yaratilmoqda…' : 'Hisobot' }}
          </button>
          <span v-if="loadMs !== null" class="xs muted num">Karta {{ loadMs }} ms da ochildi</span>
        </div>
      </header>

      <nav class="sd-nav" aria-label="Karta bo‘limlari">
        <button v-for="s in SECTIONS" :key="s.id" class="sd-nav-item" @click="jump(s.id)">{{ s.label }}</button>
      </nav>

      <!-- 1. Xavf, ishonch, sifat -->
      <section id="xavf" class="sd-row sd-row-risk">
        <RiskScorePanel :risk="detail.risk" @why="whyOpen = true" />
        <TrustPanels
          :risk="detail.risk"
          :history-months="detail.history_months"
          :source-count="detail.source_count"
          :dimensions="meta.meta?.dq_dimensions ?? {}"
          :low-dq="meta.meta?.dq_low_threshold ?? 60"
        />
      </section>

      <!-- 2. Sabablar -->
      <section id="sabablar" class="card sd-block">
        <div class="card-head">
          <div>
            <div class="card-title">3 ta asosiy sabab</div>
            <div class="card-sub">Xavf bahosiga eng katta ta’sir ko‘rsatgan omillar. To‘liq ro‘yxat — «NEGA?» oynasida.</div>
          </div>
          <button class="btn btn-sm" @click="whyOpen = true">Barcha omillar</button>
        </div>
        <div class="card-body">
          <RiskFactorList :factors="detail.factors" :score="detail.risk.score" :limit="3" class="top3" />
        </div>
      </section>

      <!-- 3. Vaqt bo'yicha og'ish va taqqoslash -->
      <section class="sd-row sd-row-time">
        <div id="vaqt" class="card">
          <div class="card-head">
            <div>
              <div class="card-title">Vaqt bo‘yicha og‘ish</div>
              <div class="card-sub">24 oy · subyekt qiymati, o‘xshashlar medianasi va kutilgan oraliq</div>
            </div>
            <select v-model="tsMetric" class="select ts-select" aria-label="Ko‘rsatkich">
              <option value="turnover">Aylanma</option>
              <option value="tx_count">Operatsiyalar soni</option>
              <option value="avg_check">O‘rtacha chek</option>
              <option value="tax_index">Soliq yuklamasi indeksi</option>
            </select>
          </div>
          <div class="card-body">
            <TimeSeriesChart v-if="ts" :series="ts" />
            <LoadingSkeleton v-else block :height="320" />
            <p v-if="ts" class="xs muted">
              {{ ts.label }}, {{ ts.unit }}. Kutilgan oraliq — o‘tgan yilning shu oyi × soha bo‘yicha yillik o‘zgarishning P10–P90 oralig‘i.
              Qizil halqa — oraliqdan tashqaridagi og‘ish. Manba: {{ ts.source }}.
            </p>
          </div>
        </div>
        <div id="taqqoslash" class="card">
          <div class="card-head">
            <div>
              <div class="card-title">O‘xshashlar bilan taqqoslash</div>
              <div class="card-sub">Soha, hudud va hajm guruhi bo‘yicha</div>
            </div>
          </div>
          <div class="card-body">
            <PeerBenchmark v-if="peers" :peers="peers" />
            <LoadingSkeleton v-else :lines="6" />
          </div>
        </div>
      </section>

      <!-- 4. Aloqadorliklar -->
      <section id="aloqadorlik" class="card sd-block">
        <div class="card-head">
          <div>
            <div class="card-title">Aloqadorliklar</div>
            <div class="card-sub" v-if="rel">
              To‘g‘ridan-to‘g‘ri aloqalar: {{ rel.summary.direct }} · shundan xavfli: {{ rel.summary.risky_direct }} ·
              2-darajada ko‘rsatilgan: {{ rel.summary.second_level_shown }} · yashirilgan periferiya: {{ rel.summary.hidden }}
            </div>
          </div>
        </div>
        <div class="card-body">
          <RelationshipGraph
            v-if="rel"
            v-model:depth="relDepth"
            :data="rel"
            :height="420"
            @open="(c) => router.push({ name: 'subject', params: { code: c } })"
          />
          <LoadingSkeleton v-else block :height="420" />
        </div>
      </section>

      <!-- 5. SI izohi va 6. Ekspert qarori -->
      <section class="sd-row sd-row-final">
        <div id="izoh" class="card">
          <div class="card-head">
            <div>
              <div class="card-title">SI izohi</div>
              <div class="card-sub">Hisoblangan natijalarning o‘zbek tilidagi tushuntirishi</div>
            </div>
          </div>
          <div class="card-body">
            <AiExplanation
              v-if="explanation"
              :explanation="explanation"
              :can-regenerate="auth.can('decisions.write')"
              :busy="regenerating"
              @regenerate="regenerate"
            />
            <LoadingSkeleton v-else :lines="6" />
          </div>
        </div>
        <div id="qaror" class="card">
          <div class="card-head">
            <div>
              <div class="card-title">Ekspert qarori</div>
              <div class="card-sub">Yakuniy operatsion qaror vakolatli ekspert tomonidan qabul qilinadi</div>
            </div>
          </div>
          <div class="card-body">
            <ExpertDecisionPanel :code="detail.code" :decisions="decisions" @saved="onDecision" />
          </div>
        </div>
      </section>

      <p class="sd-foot xs muted">
        Ro‘yxatdan o‘tgan sana: {{ date(detail.registered_at) }} · Manbalar: {{ detail.source_count }} ta · Birlashtirilgan takroriy yozuvlar:
        {{ detail.duplicate_records }} ta · Ma’lumot versiyasi: {{ detail.risk.data_version }}.
        Mazkur baho avtomatik tahlil natijasi bo‘lib, yakuniy huquqiy xulosa hisoblanmaydi.
      </p>

      <ExplanationDrawer :open="whyOpen" :code="detail.code" :risk="detail.risk" :factors="detail.factors" @close="whyOpen = false" />
    </template>

    <div v-else class="stack">
      <div class="card card-pad"><LoadingSkeleton :lines="3" /></div>
      <div class="sd-row sd-row-risk">
        <div class="card card-pad"><LoadingSkeleton :lines="8" /></div>
        <div class="card card-pad"><LoadingSkeleton :lines="8" /></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.back { margin: -6px 0 10px -8px; }

.sd-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 22px;
  margin-bottom: 12px;
}

.sd-code { font-size: 26px; font-weight: 750; letter-spacing: -0.01em; }
.sd-meta { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 10px; color: var(--text-2); font-size: var(--fs-md); }
.sd-meta span { display: inline-flex; align-items: center; gap: 6px; }
.sd-meta svg { color: var(--muted); }
.sd-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }

.sd-nav {
  position: sticky;
  top: var(--topbar-h);
  z-index: 30;
  display: flex;
  gap: 4px;
  padding: 8px 0 10px;
  margin-bottom: 6px;
  background: linear-gradient(var(--bg) 80%, rgba(245, 249, 253, 0));
}

.sd-nav-item {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: #fff;
  color: var(--text-2);
  font-size: var(--fs-sm);
  font-weight: 560;
  cursor: pointer;
  transition: all var(--t-fast);
}

.sd-nav-item:hover { border-color: var(--blue-100); color: var(--blue-600); background: var(--blue-50); }
.sd-row { display: grid; gap: var(--gap); margin-bottom: var(--gap); scroll-margin-top: 120px; }
.sd-row-risk { grid-template-columns: minmax(340px, 4fr) minmax(0, 7fr); }
.sd-row-time { grid-template-columns: minmax(0, 8fr) minmax(320px, 4fr); }
.sd-row-final { grid-template-columns: minmax(0, 6fr) minmax(0, 5fr); align-items: start; }
.sd-block { margin-bottom: var(--gap); }
section, .card[id] { scroll-margin-top: 120px; }
.top3 { display: grid !important; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.ts-select { width: 210px; height: 32px; font-size: var(--fs-sm); }
.sd-foot { margin-top: 4px; }
</style>
