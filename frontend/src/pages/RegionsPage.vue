<script setup lang="ts">
import { ArrowRight } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SectorRiskChart from '@/components/charts/SectorRiskChart.vue'
import UzbekistanMap from '@/components/map/UzbekistanMap.vue'
import ConfidenceBadge from '@/components/risk/ConfidenceBadge.vue'
import RiskBadge from '@/components/risk/RiskBadge.vue'
import RiskTypeTag from '@/components/risk/RiskTypeTag.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { dashboardApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import type { Dashboard, RegionStat } from '@/types/api'
import { num, relative } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const meta = useMetaStore()
const regions = ref<RegionStat[]>([])
const detail = ref<Dashboard | null>(null)
const error = ref(false)
const sortKey = ref<keyof RegionStat>('risk_index')

const selected = computed(() => (route.params.id as string | undefined) ?? auth.regionScope ?? null)
const sorted = computed(() => [...regions.value].sort((a, b) => Number(b[sortKey.value] ?? -1) - Number(a[sortKey.value] ?? -1)))

async function load() {
  error.value = false
  try {
    const d = await dashboardApi.get(selected.value)
    regions.value = d.regions
    detail.value = selected.value ? d : null
  } catch {
    error.value = true
  }
}

function select(id: string | null) {
  router.push(id ? { name: 'region', params: { id } } : { name: 'regions' })
}

watch(selected, load)
onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Hududlar{{ selected ? `: ${meta.regionName(selected)}` : '' }}</h1>
        <p class="page-sub">14 ma’muriy birlik kesimida analitik xavf ko‘rsatkichlari. Rasmiy statistika ko‘rsatkichlari bu yerda keltirilmaydi.</p>
      </div>
      <button v-if="selected && !auth.regionScope" class="btn btn-sm" @click="select(null)">Barcha hududlar</button>
    </div>

    <StateBlock v-if="error" kind="server-error" class="card" @retry="load" />
    <template v-else>
      <div class="reg-grid">
        <div class="card card-pad"><UzbekistanMap :regions="regions" :selected="selected" :height="380" @select="select" /></div>
        <div class="card">
          <table class="table">
            <thead>
              <tr>
                <th>Hudud</th>
                <th class="right"><button class="th" @click="sortKey = 'subjects'">Subyektlar</button></th>
                <th class="right"><button class="th" @click="sortKey = 'high'">Yuqori</button></th>
                <th class="right"><button class="th" @click="sortKey = 'risk_index'">Ko‘rsatkich</button></th>
                <th class="right"><button class="th" @click="sortKey = 'avg_dq'">Sifat</button></th>
                <th class="right"><button class="th" @click="sortKey = 'new_alerts'">Yangi</button></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in sorted" :key="r.id" class="clickable" :class="{ sel: r.id === selected, dim: r.restricted }" @click="!r.restricted && select(r.id)">
                <td>{{ r.name }}</td>
                <template v-if="r.restricted"><td colspan="5" class="xs muted right">Ruxsat mavjud emas</td></template>
                <template v-else>
                  <td class="right num">{{ num(r.subjects) }}</td>
                  <td class="right num">{{ num(r.high) }}</td>
                  <td class="right num"><b>{{ num(r.risk_index, 1) }}%</b></td>
                  <td class="right num">{{ num(r.avg_dq, 1) }}</td>
                  <td class="right num">{{ num(r.new_alerts) }}</td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <template v-if="selected">
        <div v-if="!detail" class="card card-pad"><LoadingSkeleton :lines="6" /></div>
        <div v-else class="drill">
          <div class="card card-pad">
            <div class="card-title">Soha kesimida</div>
            <SectorRiskChart :sectors="detail.sectors" />
          </div>
          <div class="card">
            <div class="card-head">
              <div><div class="card-title">Yuqori ustuvorlikdagi holatlar</div><div class="card-sub">Yangilangan: {{ relative(detail.kpis.last_update) }}</div></div>
              <RouterLink :to="{ name: 'subjects', query: { region: selected, level: 'attention' } }" class="btn btn-sm">Barchasi <ArrowRight :size="14" /></RouterLink>
            </div>
            <div class="card-body cases">
              <RouterLink v-for="c in detail.top_cases" :key="c.code" :to="{ name: 'subject', params: { code: c.code } }" class="case">
                <span class="code">{{ c.code }}</span>
                <span class="muted xs">{{ meta.sectorName(c.sector_id) }}</span>
                <RiskTypeTag :code="c.primary_risk_type" :show-name="false" />
                <span class="spacer" />
                <RiskBadge :level="c.level" :score="c.score" size="sm" />
                <ConfidenceBadge :level="c.confidence" size="sm" prefix />
              </RouterLink>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.reg-grid { display: grid; grid-template-columns: minmax(0, 6fr) minmax(0, 5fr); gap: var(--gap); margin-bottom: var(--gap); }
.th { border: 0; background: none; padding: 0; font: inherit; color: inherit; text-transform: inherit; letter-spacing: inherit; cursor: pointer; }
tr.sel td { background: var(--blue-50); }
tr.dim { opacity: 0.55; cursor: default; }
.drill { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 6fr); gap: var(--gap); }
.cases { display: flex; flex-direction: column; gap: 2px; }
.case { display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 8px; color: inherit; text-decoration: none; }
.case:hover { background: var(--surface-3); text-decoration: none; }
</style>
