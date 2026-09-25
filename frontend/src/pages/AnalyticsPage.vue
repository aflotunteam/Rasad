<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { axisCommon, baseTooltip, FONT } from '@/components/charts/echarts'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { dashboardApi, subjectsApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import type { Dashboard, SubjectRow } from '@/types/api'
import { num } from '@/utils/format'
import { RISK_TYPE_ICON } from '@/utils/icons'
import { HEX, LEVEL_HEX } from '@/utils/labels'

const auth = useAuthStore()
const meta = useMetaStore()
const dash = ref<Dashboard | null>(null)
const sample = ref<SubjectRow[]>([])
const error = ref(false)

const METHODS = [
  { name: 'Qoidalar va statistik og‘ish', desc: 'Soha, hudud va hajm guruhidagi o‘xshashlarga nisbatan robust z-og‘ish (mediana va MAD).', types: 'R01, R02, R03, R04, R06' },
  { name: 'Anomaliya modeli', desc: 'Isolation Forest: bir nechta belgining g‘ayrioddiy birikmasini aniqlaydi.', types: 'R08' },
  { name: 'Vaqt modeli', desc: 'Yillik o‘zgarishlarni soha mavsumiy qonuniyati bilan taqqoslaydi.', types: 'R07' },
  { name: 'Graf modeli', desc: 'Xavfi yuqori subyektlar bilan tuzilmaviy aloqalar (muassis, rahbar, manzil).', types: 'R05' },
  { name: 'Kalibrlash', desc: 'Vaznli signallar monoton funksiya bilan 0–100 shkalaga o‘tkaziladi. MVP vaznlari ekspert tomonidan belgilangan.', types: '—' },
]

async function load() {
  error.value = false
  try {
    const region = auth.regionScope ?? undefined
    const [d, low, mid, top] = await Promise.all([
      dashboardApi.get(region),
      subjectsApi.list({ dq: 'low', page_size: 200, region }),
      subjectsApi.list({ dq: 'medium', page_size: 200, region }),
      subjectsApi.list({ level: 'attention', page_size: 200, region }),
    ])
    dash.value = d
    sample.value = [...low.items, ...mid.items, ...top.items]
  } catch {
    error.value = true
  }
}

const typeCount = computed(() => new Map(dash.value?.risk_types.map((t) => [t.code, t.count]) ?? []))

const distOption = computed(() => {
  const d = dash.value?.distribution ?? []
  const { low, high } = meta.thresholds
  return {
    textStyle: { fontFamily: FONT },
    grid: { left: 6, right: 10, top: 16, bottom: 4, containLabel: true },
    tooltip: { ...baseTooltip, trigger: 'axis' },
    xAxis: { type: 'category', data: d.map((b) => `${b.from}–${b.to}`), ...axisCommon, splitLine: { show: false } },
    yAxis: { type: 'log', ...axisCommon, splitNumber: 3 },
    series: [{
      type: 'bar', barWidth: '62%',
      data: d.map((b) => ({ value: Math.max(b.count, 0.9), itemStyle: { color: b.from >= high ? LEVEL_HEX.high : b.from >= low ? LEVEL_HEX.medium : '#B7C3D3', borderRadius: [3, 3, 0, 0] } })),
    }],
  }
})

const scatterOption = computed(() => ({
  textStyle: { fontFamily: FONT },
  grid: { left: 6, right: 16, top: 16, bottom: 26, containLabel: true },
  tooltip: { ...baseTooltip, formatter: (p: { data: [number, number, string] }) => `${p.data[2]}<br/>Ma’lumot sifati: ${num(p.data[0], 1)}<br/>Ishonch: ${num(p.data[1], 0)}` },
  xAxis: { type: 'value', name: 'Ma’lumot sifati', nameLocation: 'middle', nameGap: 26, min: 20, max: 100, ...axisCommon },
  yAxis: { type: 'value', name: 'Ishonch', min: 0, max: 100, ...axisCommon },
  series: [{
    type: 'scatter', symbolSize: 6,
    data: sample.value.map((s) => [s.dq_score, s.confidence_value * 100, s.code]),
    itemStyle: { color: HEX.blue, opacity: 0.55 },
    markLine: { symbol: 'none', silent: true, lineStyle: { color: HEX.medium, type: 'dashed' }, label: { formatter: 'past sifat chegarasi', fontSize: 10, color: HEX.muted }, data: [{ xAxis: 60 }] },
  }],
}))

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Tahlillar</h1>
        <p class="page-sub">Xavf tasnifi, tahlil usullari va natijalar taqsimoti. RASAD bir nechta usulni birlashtiradi va har birining hissasini ko‘rsatadi.</p>
      </div>
    </div>
    <StateBlock v-if="error" kind="server-error" class="card" @retry="load" />
    <div v-else-if="!dash" class="card card-pad"><LoadingSkeleton :lines="10" /></div>
    <template v-else>
      <section class="tax">
        <article v-for="t in meta.meta?.risk_types" :key="t.code" class="card tax-card">
          <div class="row"><span class="tax-icon"><component :is="RISK_TYPE_ICON[t.code]" :size="17" /></span><b class="tax-code">{{ t.code }}</b><span class="spacer" /><span class="num tax-n">{{ num(typeCount.get(t.code) ?? 0) }}</span></div>
          <div class="tax-name">{{ t.name }}</div>
          <p class="xs muted">{{ t.description }}</p>
        </article>
      </section>

      <section class="an-grid">
        <div class="card">
          <div class="card-head"><div><div class="card-title">Xavf bahosi taqsimoti</div><div class="card-sub">Logarifmik shkala · rang daraja chegarasini bildiradi</div></div></div>
          <div class="card-body"><VChart :option="distOption" autoresize style="height: 260px" /></div>
        </div>
        <div class="card">
          <div class="card-head"><div><div class="card-title">Ma’lumot sifati va ishonch</div><div class="card-sub">Past sifat → past ishonch. Tanlanma: sifati past/o‘rta va e’tibor talab qiluvchi subyektlar</div></div></div>
          <div class="card-body"><VChart :option="scatterOption" autoresize style="height: 260px" /></div>
        </div>
      </section>

      <section class="card">
        <div class="card-head"><div><div class="card-title">Tahlil usullari</div><div class="card-sub">Faol model: {{ meta.meta?.active_model?.name }} v{{ meta.meta?.active_model?.version }}</div></div></div>
        <table class="table">
          <thead><tr><th>Usul</th><th>Tavsif</th><th>Xavf turlari</th></tr></thead>
          <tbody><tr v-for="m in METHODS" :key="m.name"><td><b>{{ m.name }}</b></td><td class="small">{{ m.desc }}</td><td class="small num">{{ m.types }}</td></tr></tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<style scoped>
.tax { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--gap); margin-bottom: var(--gap); }
.tax-card { padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; }
.tax-icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 8px; background: var(--blue-50); color: var(--blue); }
.tax-code { color: var(--navy); }
.tax-n { font-size: var(--fs-lg); font-weight: 700; color: var(--navy); }
.tax-name { font-weight: 620; color: var(--navy); }
.an-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap); margin-bottom: var(--gap); }
</style>
