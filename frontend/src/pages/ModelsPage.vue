<script setup lang="ts">
import { ShieldAlert, ShieldCheck } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { axisCommon, baseTooltip, FONT } from '@/components/charts/echarts'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { dataApi, modelsApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import type { ModelRow, Monitoring } from '@/types/api'
import { date, monthYear, num } from '@/utils/format'
import { HEX, MODEL_STATUS_LABEL } from '@/utils/labels'

const auth = useAuthStore()
const ui = useUiStore()
const models = ref<ModelRow[] | null>(null)
const mon = ref<Monitoring | null>(null)
const error = ref(false)
const canWrite = computed(() => auth.can('models.write'))

async function load() {
  error.value = false
  try {
    ;[models.value, mon.value] = await Promise.all([modelsApi.list(), modelsApi.monitoring()])
  } catch {
    error.value = true
  }
}

async function setStatus(m: ModelRow, status: string) {
  try {
    await modelsApi.setStatus(m.id, status)
    ui.toast(`${m.name} v${m.version}: ${MODEL_STATUS_LABEL[status]}`, 'success')
    load()
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Holatni o‘zgartirib bo‘lmadi', 'error')
  }
}

async function recompute() {
  try {
    const job = await dataApi.recompute()
    ui.toast(`Qayta hisoblash navbatga qo‘yildi (vazifa #${job.id})`, 'info')
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Ishga tushirib bo‘lmadi', 'error')
  }
}

function metricText(m: ModelRow): string {
  const x = m.metrics
  if (typeof x.auc === 'number') return `AUC ${num(x.auc, 3)} · P@5% ${num(Number(x.precision_at_5pct), 3)}`
  return String(x.note ?? 'Ma’lumot mavjud emas')
}

function lineChart(title: string, values: (number | null)[], fmt: (v: number) => string, limit?: number) {
  const s = mon.value?.series ?? []
  return {
    textStyle: { fontFamily: FONT },
    title: { text: title, left: 0, top: 0, textStyle: { fontSize: 12.5, fontWeight: 600, color: HEX.navy, fontFamily: FONT } },
    grid: { left: 6, right: 14, top: 34, bottom: 4, containLabel: true },
    tooltip: { ...baseTooltip, trigger: 'axis', valueFormatter: (v: number) => fmt(v) },
    xAxis: { type: 'category', data: s.map((p) => monthYear(p.period, true)), ...axisCommon, splitLine: { show: false } },
    yAxis: { type: 'value', ...axisCommon, axisLabel: { ...axisCommon.axisLabel, formatter: fmt }, splitNumber: 3 },
    series: [{
      type: 'line', data: values, symbolSize: 6, lineStyle: { color: HEX.blue, width: 2 }, itemStyle: { color: HEX.blue },
      markLine: limit === undefined ? undefined : { symbol: 'none', silent: true, lineStyle: { color: HEX.high, type: 'dashed' }, label: { formatter: 'chegara', color: HEX.high, fontSize: 10 }, data: [{ yAxis: limit }] },
    }],
  }
}

const charts = computed(() => {
  if (!mon.value) return []
  const s = mon.value.series
  return [
    lineChart('Ma’lumot og‘ishi (PSI)', s.map((p) => p.psi), (v) => num(v, 2), mon.value.limits.psi),
    lineChart('O‘rtacha ishonch darajasi', s.map((p) => p.mean_confidence * 100), (v) => num(v, 1)),
    lineChart('Noodatiy holatlar soni', s.map((p) => p.anomalies), (v) => num(v, 0)),
    lineChart('Ekspert rad etish darajasi', mon.value.rejection.slice(-6).map((r) => (r.rate ?? 0) * 100), (v) => `${num(v, 0)}%`, mon.value.limits.rejection_rate * 100),
  ]
})

const distChart = computed(() => {
  const last = mon.value?.series.at(-1)
  if (!last) return null
  return {
    textStyle: { fontFamily: FONT },
    title: { text: 'Natija taqsimoti (joriy davr)', left: 0, top: 0, textStyle: { fontSize: 12.5, fontWeight: 600, color: HEX.navy, fontFamily: FONT } },
    grid: { left: 6, right: 10, top: 34, bottom: 4, containLabel: true },
    tooltip: { ...baseTooltip, trigger: 'axis' },
    xAxis: { type: 'category', data: last.distribution.map((_, i) => `${i * 10}–${i * 10 + 10}`), ...axisCommon, splitLine: { show: false } },
    yAxis: { type: 'log', ...axisCommon, splitNumber: 3 },
    series: [{ type: 'bar', data: last.distribution.map((v) => Math.max(v, 0.9)), barWidth: '60%', itemStyle: { color: HEX.navy, borderRadius: [3, 3, 0, 0] } }],
  }
})

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Modellar</h1>
        <p class="page-sub">Modellar reestri va monitoring. Tekshirilmagan model faol bo‘la olmaydi.</p>
      </div>
      <button v-if="auth.can('settings.write')" class="btn btn-sm" @click="recompute">Qayta hisoblashni ishga tushirish</button>
    </div>

    <StateBlock v-if="error" kind="server-error" class="card" @retry="load" />
    <div v-else-if="!models || !mon" class="card card-pad"><LoadingSkeleton :lines="8" /></div>
    <template v-else>
      <div class="notice mon-status" :class="mon.status === 'normal' ? 'notice-info' : 'notice-warn'">
        <component :is="mon.status === 'normal' ? ShieldCheck : ShieldAlert" :size="18" />
        <div>
          <b>{{ mon.status_message }}</b>
          <div v-for="w in mon.warnings" :key="w.code" class="small">{{ w.message }}</div>
          <div class="xs">PSI: {{ num(mon.current.psi, 3) }} (chegara {{ num(mon.limits.psi, 2) }}) · Rad etish darajasi: {{ num((mon.current.rejection_rate ?? 0) * 100, 1) }}% (chegara {{ num(mon.limits.rejection_rate * 100, 0) }}%)</div>
        </div>
      </div>

      <section class="card reg">
        <div class="card-head"><div><div class="card-title">Modellar reestri</div><div class="card-sub">Holatlar: Qoralama → Sinovda → Tasdiqlangan → Faol → Arxivlangan</div></div></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Model</th><th>Versiya</th><th>Algoritm</th><th>Holat</th><th>Tasdiqlangan sana</th><th>Sifat ko‘rsatkichlari</th><th>Drift</th><th>Tasdiqlagan shaxs</th><th v-if="canWrite">Amal</th></tr></thead>
            <tbody>
              <tr v-for="m in models" :key="m.id">
                <td><b>{{ m.name }}</b><div class="xs muted">{{ m.key }}</div></td>
                <td class="num">v{{ m.version }}</td>
                <td class="small alg">{{ m.algorithm }}</td>
                <td><span class="ms" :class="`ms-${m.status}`">{{ MODEL_STATUS_LABEL[m.status] }}</span></td>
                <td class="small">{{ date(m.approved_at) }}</td>
                <td class="small">{{ metricText(m) }}<div v-if="m.metrics.note && typeof m.metrics.auc === 'number'" class="xs muted">{{ m.metrics.note }}</div></td>
                <td class="small num">{{ m.drift.psi !== undefined ? `PSI ${num(m.drift.psi, 3)}` : '—' }}</td>
                <td class="small">{{ m.approved_by ?? '—' }}</td>
                <td v-if="canWrite">
                  <select class="select sm" :value="''" :disabled="!m.allowed_transitions.length" @change="setStatus(m, ($event.target as HTMLSelectElement).value)">
                    <option value="" disabled>O‘tkazish…</option>
                    <option v-for="t in m.allowed_transitions" :key="t" :value="t">{{ MODEL_STATUS_LABEL[t] }}</option>
                    <option v-if="m.status === 'TESTING'" value="ACTIVE">Faol (tasdiqsiz)</option>
                  </select>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="mon-grid">
        <div v-for="(c, i) in charts" :key="i" class="card card-pad"><VChart :option="c" autoresize style="height: 190px" /></div>
        <div v-if="distChart" class="card card-pad"><VChart :option="distChart" autoresize style="height: 190px" /></div>
        <div class="card card-pad xs muted note">
          Monitoring ko‘rsatkichlari har oy oxirigacha bo‘lgan ma’lumotlar bo‘yicha modelni qayta hisoblash orqali olingan.
          Sifat ko‘rsatkichlari sintetik namoyish ma’lumotlarida o‘lchangan va real samaradorlikni anglatmaydi.
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.mon-status { margin-bottom: var(--gap); align-items: flex-start; }
.reg { margin-bottom: var(--gap); }
.alg { max-width: 260px; }
.ms { display: inline-flex; padding: 2px 9px; border-radius: 999px; font-size: var(--fs-xs); font-weight: 650; background: var(--surface-3); color: var(--text-2); }
.ms-ACTIVE { background: var(--navy); color: #fff; }
.ms-APPROVED { background: var(--blue-50); color: var(--blue-600); }
.ms-TESTING { background: var(--cyan-50); color: #0b6f9c; }
.ms-ARCHIVED { color: var(--muted); }
.select.sm { height: 30px; width: 150px; font-size: var(--fs-sm); }
.mon-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--gap); }
.note { display: flex; align-items: center; line-height: 1.55; }
</style>
