<script setup lang="ts">
// O'xshash subyektlar bilan taqqoslash: P10–P90 oraliq, kvartillar, mediana va subyekt nuqtasi.
// Soxta 3D yoki bezakli grafiklar ishlatilmaydi.
import { computed, ref } from 'vue'
import type { Peers } from '@/types/api'
import { num, withUnit } from '@/utils/format'

const props = defineProps<{ peers: Peers }>()
const metricIdx = ref(0)
const m = computed(() => props.peers.metrics[metricIdx.value])

const scale = computed(() => {
  const g = m.value.groups
  if (!g.length || m.value.value === null) return { lo: 0, hi: 1 }
  const lo = Math.min(m.value.value, ...g.map((x) => x.p10))
  const hi = Math.max(m.value.value, ...g.map((x) => x.p90))
  const pad = (hi - lo) * 0.08 || 1
  return { lo: lo - pad, hi: hi + pad }
})

function x(v: number) {
  const { lo, hi } = scale.value
  return ((v - lo) / (hi - lo)) * 100
}

function pctText(p: number) {
  if (p >= 90) return 'guruhning eng yuqori 10 foizida'
  if (p <= 10) return 'guruhning eng past 10 foizida'
  return `${num(p, 0)}-persentil`
}
</script>

<template>
  <div class="peer">
    <div class="peer-tabs" role="tablist">
      <button
        v-for="(mt, i) in peers.metrics"
        :key="mt.metric"
        role="tab"
        :aria-selected="i === metricIdx"
        class="peer-tab"
        :class="{ active: i === metricIdx }"
        @click="metricIdx = i"
      >
        {{ mt.label }}
      </button>
    </div>

    <div v-if="m.value === null" class="muted small">Ma’lumot mavjud emas</div>
    <template v-else>
      <div class="peer-value">
        <span class="xs muted">Subyekt qiymati</span>
        <b class="num">{{ withUnit(m.value, m.unit) }}</b>
      </div>
      <div v-for="g in m.groups" :key="g.group" class="peer-row">
        <div class="peer-label">
          <span>{{ g.label }}</span>
          <span class="xs muted num">n = {{ num(g.n) }} · {{ pctText(g.percentile) }}</span>
        </div>
        <div class="peer-track" :title="`P10 ${num(g.p10, 1)} · P25 ${num(g.p25, 1)} · Mediana ${num(g.median, 1)} · P75 ${num(g.p75, 1)} · P90 ${num(g.p90, 1)}`">
          <i class="whisker" :style="{ left: `${x(g.p10)}%`, width: `${x(g.p90) - x(g.p10)}%` }" />
          <i class="box" :style="{ left: `${x(g.p25)}%`, width: `${Math.max(0.6, x(g.p75) - x(g.p25))}%` }" />
          <i class="median" :style="{ left: `${x(g.median)}%` }" />
          <i class="me" :class="{ out: g.percentile >= 90 || g.percentile <= 10 }" :style="{ left: `${x(m.value)}%` }" />
        </div>
      </div>
      <div class="peer-legend xs muted">
        <span><i class="lg-whisker" /> P10–P90</span>
        <span><i class="lg-box" /> P25–P75</span>
        <span><i class="lg-median" /> Mediana</span>
        <span><i class="lg-me" /> Subyekt</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.peer { display: flex; flex-direction: column; gap: 12px; }
.peer-tabs { display: flex; flex-wrap: wrap; gap: 4px; }

.peer-tab {
  padding: 5px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: #fff;
  color: var(--text-2);
  font-size: var(--fs-xs);
  font-weight: 560;
  cursor: pointer;
  transition: all var(--t-fast);
}

.peer-tab.active { background: var(--navy); border-color: var(--navy); color: #fff; }
.peer-value { display: flex; align-items: baseline; justify-content: space-between; }
.peer-value b { font-size: var(--fs-lg); color: var(--navy); }
.peer-row { display: flex; flex-direction: column; gap: 6px; }
.peer-label { display: flex; justify-content: space-between; gap: 8px; font-size: var(--fs-sm); color: var(--text-2); }
.peer-track { position: relative; height: 22px; border-radius: 5px; background: var(--surface-2); border: 1px solid var(--border); }
.peer-track i { position: absolute; top: 50%; transform: translateY(-50%); display: block; }
.whisker { height: 2px; background: #9fb3cc; }
.box { height: 10px; background: #c8daf3; border: 1px solid #9fbbe6; border-radius: 3px; }
.median { width: 2px; height: 14px; background: var(--navy-3); margin-left: -1px; }
.me { width: 12px; height: 12px; margin-left: -6px; border-radius: 50%; background: var(--navy); border: 2px solid #fff; box-shadow: 0 0 0 1px var(--navy); }
.me.out { background: var(--risk-high); box-shadow: 0 0 0 1px var(--risk-high); }
.peer-legend { display: flex; gap: 12px; flex-wrap: wrap; }
.peer-legend span { display: inline-flex; align-items: center; gap: 5px; }
.peer-legend i { display: inline-block; }
.lg-whisker { width: 14px; height: 2px; background: #9fb3cc; }
.lg-box { width: 14px; height: 8px; background: #c8daf3; border: 1px solid #9fbbe6; border-radius: 2px; }
.lg-median { width: 2px; height: 10px; background: var(--navy-3); }
.lg-me { width: 9px; height: 9px; border-radius: 50%; background: var(--navy); }
</style>
