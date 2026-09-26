<script setup lang="ts">
import {
  ArrowRight,
  Bell,
  BrainCircuit,
  Building2,
  Clock3,
  Database,
  OctagonAlert,
  X,
} from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import RiskTrendChart from '@/components/charts/RiskTrendChart.vue'
import SectorRiskChart from '@/components/charts/SectorRiskChart.vue'
import UzbekistanMap from '@/components/map/UzbekistanMap.vue'
import AnalyticChain from '@/components/risk/AnalyticChain.vue'
import ConfidenceBadge from '@/components/risk/ConfidenceBadge.vue'
import MetricCard from '@/components/risk/MetricCard.vue'
import RiskBadge from '@/components/risk/RiskBadge.vue'
import RiskTypeTag from '@/components/risk/RiskTypeTag.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { dashboardApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { useUiStore } from '@/stores/ui'
import type { Dashboard } from '@/types/api'
import { num, relative } from '@/utils/format'
import { RISK_TYPE_ICON } from '@/utils/icons'

const router = useRouter()
const auth = useAuthStore()
const meta = useMetaStore()
const ui = useUiStore()
const data = ref<Dashboard | null>(null)
const allRegions = ref<Dashboard['regions']>([])
const loading = ref(true)
const error = ref(false)

const region = computed(() => auth.regionScope ?? ui.region)
const regionStat = computed(() => allRegions.value.find((r) => r.id === region.value) ?? null)

async function load() {
  loading.value = true
  error.value = false
  try {
    const d = await dashboardApi.get(region.value)
    data.value = d
    allRegions.value = d.regions
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

function selectRegion(id: string | null) {
  if (auth.regionScope) return
  ui.region = id
}

watch(region, load)
onMounted(load)

const maxType = computed(() => Math.max(1, ...(data.value?.risk_types.map((t) => t.count) ?? [1])))
const typeRows = computed(() =>
  (meta.meta?.risk_types ?? []).map((t) => ({
    ...t,
    count: data.value?.risk_types.find((r) => r.code === t.code)?.count ?? 0,
  })),
)

function openCases() {
  router.push({ name: 'subjects', query: { ...(region.value ? { region: region.value } : {}), level: 'high' } })
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Bosh sahifa</h1>
        <p class="page-sub">
          Iqtisodiy xavf signallari: nima bo‘lyapti, qayerda, nimaga birinchi navbatda e’tibor kerak va nima sababdan.
        </p>
      </div>
      <div class="row">
        <span v-if="region" class="chip chip-info region-chip">
          {{ meta.regionName(region) }}
          <button v-if="!auth.regionScope" class="chip-x" aria-label="Hudud filtrini olib tashlash" @click="selectRegion(null)">
            <X :size="12" />
          </button>
        </span>
        <span v-else class="chip">Barcha hududlar</span>
      </div>
    </div>

    <StateBlock v-if="error" kind="server-error" class="card" @retry="load" />

    <template v-else>
      <!-- KPI qatori -->
      <section class="kpis" aria-label="Asosiy ko‘rsatkichlar">
        <template v-if="data">
          <MetricCard label="Tahlil qilingan subyektlar" :value="num(data.kpis.analyzed)" :icon="Building2" tone="navy" hint="Sintetik, rasmiy tuzilmaga moslashtirilgan" />
          <MetricCard
            label="Yuqori ustuvorlikdagi holatlar"
            :value="num(data.kpis.high_priority)"
            :icon="OctagonAlert"
            tone="high"
            :hint="`O‘rta darajada: ${num(data.kpis.medium_priority)}`"
            :to="{ name: 'subjects', query: { ...(region ? { region } : {}), level: 'high' } }"
          />
          <MetricCard
            label="Yangi ogohlantirishlar"
            :value="num(data.kpis.new_alerts)"
            :icon="Bell"
            tone="blue"
            :hint="`Oxirgi 7 kunda: ${num(data.kpis.new_alerts_7d)}`"
            :to="auth.can('alerts.read') ? { name: 'alerts' } : undefined"
          />
          <MetricCard
            label="O‘rtacha ma’lumot sifati"
            :value="`${num(data.kpis.avg_dq, 1)} / 100`"
            :icon="Database"
            tone="cyan"
            :hint="`Sifati past subyektlar: ${num(data.kpis.low_dq_subjects)}`"
          />
          <MetricCard label="Faol model" :value="data.kpis.active_model?.replace('RASAD Risk Engine ', '') ?? 'Model mavjud emas'" :icon="BrainCircuit" tone="neutral" hint="RASAD Risk Engine · tasdiqlangan" />
          <MetricCard label="Oxirgi yangilanish" :value="relative(data.kpis.last_update)" :icon="Clock3" tone="neutral" hint="Xavf baholari hisoblangan vaqt" />
        </template>
        <div v-for="i in data ? 0 : 6" v-else :key="i" class="card card-pad"><LoadingSkeleton :lines="2" /></div>
      </section>

      <!-- Xarita va ustuvor holatlar -->
      <section class="main-grid">
        <div class="card map-card">
          <div class="card-head">
            <div>
              <div class="card-title">O‘zbekiston hududlari kesimida xavf signallari</div>
              <div class="card-sub">Hududni tanlang: butun sahifa shu hudud bo‘yicha filtrlanadi</div>
            </div>
          </div>
          <div class="card-body">
            <UzbekistanMap :regions="allRegions" :selected="region" :height="468" @select="selectRegion" />
          </div>
        </div>

        <div class="card side-card">
          <div class="card-head">
            <div>
              <div class="card-title">Yuqori ustuvorlikdagi holatlar</div>
              <div class="card-sub">{{ region ? meta.regionName(region) : 'Barcha hududlar' }} · xavf bahosi bo‘yicha</div>
            </div>
          </div>
          <div v-if="regionStat" class="region-summary">
            <div><span class="muted xs">Subyektlar</span><b class="num">{{ num(regionStat.subjects) }}</b></div>
            <div><span class="muted xs">Yuqori</span><b class="num">{{ num(regionStat.high) }}</b></div>
            <div><span class="muted xs">O‘rta</span><b class="num">{{ num(regionStat.medium) }}</b></div>
            <div><span class="muted xs">Sifat</span><b class="num">{{ num(regionStat.avg_dq, 1) }}</b></div>
          </div>
          <div class="case-list">
            <LoadingSkeleton v-if="loading && !data" :lines="8" :height="30" />
            <StateBlock v-else-if="data && !data.top_cases.length" kind="empty" compact />
            <RouterLink
              v-for="c in data?.top_cases ?? []"
              :key="c.code"
              :to="{ name: 'subject', params: { code: c.code } }"
              class="case"
              :class="{ dim: loading }"
            >
              <div class="case-main">
                <div class="row">
                  <span class="code">{{ c.code }}</span>
                  <RiskTypeTag :code="c.primary_risk_type" :show-name="false" />
                </div>
                <div class="muted xs">{{ meta.regionShort(c.region_id) }} · {{ meta.sectorName(c.sector_id) }}</div>
              </div>
              <div class="case-badges">
                <RiskBadge :score="c.score" :level="c.level" size="sm" :show-label="false" />
                <ConfidenceBadge :level="c.confidence" size="sm" prefix />
              </div>
            </RouterLink>
          </div>
          <div class="side-foot">
            <button class="btn btn-sm btn-primary" @click="openCases">
              Barcha yuqori ustuvorlikdagi holatlar <ArrowRight :size="14" />
            </button>
            <RouterLink v-if="region" :to="{ name: 'region', params: { id: region } }" class="btn btn-sm">Hudud tahlili</RouterLink>
          </div>
        </div>
      </section>

      <!-- Tahlil zanjiri -->
      <section class="card chain-card">
        <div class="card-head">
          <div>
            <div class="card-title">RASAD tahlil zanjiri</div>
            <div class="card-sub">Har bir xavf bahosi shu bosqichlardan o‘tadi. Yakuniy qaror ekspertda qoladi.</div>
          </div>
        </div>
        <div class="card-body">
          <AnalyticChain v-if="data" :steps="data.chain" />
          <LoadingSkeleton v-else :lines="2" />
        </div>
      </section>

      <!-- Pastki qator -->
      <section class="bottom-grid">
        <div class="card">
          <div class="card-head">
            <div>
              <div class="card-title">Sohalar kesimida</div>
              <div class="card-sub">O‘rta va yuqori darajali holatlar ulushi</div>
            </div>
          </div>
          <div class="card-body">
            <SectorRiskChart v-if="data" :sectors="data.sectors" />
            <div class="legend-row xs muted">
              <span><i class="sw sw-high" /> Yuqori</span>
              <span><i class="sw sw-medium" /> O‘rta</span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-head">
            <div>
              <div class="card-title">Xavf turlari</div>
              <div class="card-sub">Asosiy xavf turi bo‘yicha e’tibor talab qiluvchi holatlar</div>
            </div>
          </div>
          <div class="card-body types">
            <RouterLink
              v-for="t in typeRows"
              :key="t.code"
              class="type-row"
              :to="{ name: 'subjects', query: { ...(region ? { region } : {}), risk_type: t.code, level: 'attention' } }"
              :title="t.description"
            >
              <component :is="RISK_TYPE_ICON[t.code]" :size="15" class="type-icon" />
              <span class="type-code">{{ t.code }}</span>
              <span class="type-name">{{ t.name }}</span>
              <span class="type-bar"><i :style="{ width: `${(t.count / maxType) * 100}%` }" /></span>
              <span class="type-count num">{{ num(t.count) }}</span>
            </RouterLink>
          </div>
        </div>

        <div class="card">
          <div class="card-head">
            <div>
              <div class="card-title">Vaqt bo‘yicha dinamika</div>
              <div class="card-sub">Yuqori ustuvorlikdagi holatlar ulushi, oylik qayta hisob</div>
            </div>
          </div>
          <div class="card-body">
            <RiskTrendChart v-if="data?.trend.length" :trend="data.trend" />
            <StateBlock v-else-if="data" kind="no-model" compact />
            <p class="xs muted trend-note">Har bir nuqta — shu oy oxirigacha bo‘lgan ma’lumotlar bo‘yicha model natijasi.</p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.region-chip { height: 30px; padding: 0 6px 0 12px; font-size: var(--fs-sm); }

.chip-x {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 50%;
  background: rgba(33, 109, 243, 0.12);
  color: var(--blue-600);
  cursor: pointer;
}

.kpis {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: var(--gap);
  margin-bottom: var(--gap);
}

.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 8fr) minmax(340px, 4fr);
  gap: var(--gap);
  margin-bottom: var(--gap);
}

.side-card { display: flex; flex-direction: column; }

.region-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 12px 20px 0;
  padding: 10px 12px;
  border-radius: var(--radius);
  background: var(--surface-2);
  border: 1px solid var(--border);
}

.region-summary div { display: flex; flex-direction: column; }
.region-summary b { font-size: var(--fs-lg); color: var(--navy); }

.case-list { flex: 1; display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; overflow: auto; max-height: 470px; }

.case {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 8px;
  border-radius: 9px;
  color: inherit;
  text-decoration: none;
  transition: background var(--t-fast) var(--ease);
}

.case:hover { background: var(--surface-3); text-decoration: none; }
.case.dim { opacity: 0.55; }
.case-main { flex: 1; min-width: 0; }
.case-badges { display: flex; align-items: center; gap: 6px; }

.side-foot {
  display: flex;
  gap: 8px;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--border);
}

.chain-card { margin-bottom: var(--gap); }

.bottom-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--gap);
}

.legend-row { display: flex; gap: 14px; margin-top: 6px; }
.legend-row span { display: inline-flex; align-items: center; gap: 5px; }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }
.sw-high { background: var(--risk-high); }
.sw-medium { background: var(--risk-medium); }

.types { display: flex; flex-direction: column; gap: 4px; }

.type-row {
  display: grid;
  grid-template-columns: 16px 30px minmax(0, 1fr) 54px 34px;
  align-items: center;
  gap: 7px;
  padding: 7px 6px;
  border-radius: 8px;
  color: inherit;
  text-decoration: none;
  font-size: var(--fs-sm);
}

.type-row:hover { background: var(--surface-3); text-decoration: none; }
.type-icon { color: var(--blue); }
.type-code { font-weight: 650; color: var(--navy); font-size: var(--fs-sm); }
.type-name { color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.type-bar { height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.type-bar i { display: block; height: 100%; background: var(--navy-3); border-radius: 3px; }
.type-count { text-align: right; font-weight: 600; color: var(--navy); }
.trend-note { margin-top: 6px; }

@media (max-width: 1320px) {
  .kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
