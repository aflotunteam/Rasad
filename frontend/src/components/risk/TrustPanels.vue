<script setup lang="ts">
// Ishonch darajasi va ma'lumot sifati: alohida ko'rsatkichlar, lekin bog'liqligi aniq ko'rsatiladi
// (past ma'lumot sifati → past ishonch). Yuqori xavf bahosi avtomatik ishonchli degani emas.
import { ArrowRight, TriangleAlert } from 'lucide-vue-next'
import { computed } from 'vue'
import ConfidenceBadge from './ConfidenceBadge.vue'
import type { Risk } from '@/types/api'
import { num } from '@/utils/format'

const props = defineProps<{ risk: Risk; historyMonths: number; sourceCount: number; dimensions: Record<string, string>; lowDq: number }>()
const low = computed(() => props.risk.dq_score < props.lowDq)
const dims = computed(() =>
  Object.entries(props.dimensions).map(([k, label]) => ({ key: k, label, value: props.risk.dq_dimensions[k] ?? 0 })),
)
</script>

<template>
  <div class="trust">
    <div class="card panel">
      <div class="section-label">Ishonch darajasi</div>
      <div class="conf-main">
        <ConfidenceBadge :level="risk.confidence" />
        <span class="conf-val num">{{ num(risk.confidence_value * 100, 0) }}<small>/100</small></span>
      </div>
      <ul class="conf-inputs">
        <li><span>Ma’lumot sifati</span><b class="num">{{ num(risk.dq_score, 1) }}</b></li>
        <li><span>Tarix uzunligi</span><b class="num">{{ historyMonths }} oy</b></li>
        <li><span>Ma’lumot manbalari</span><b class="num">{{ sourceCount }} ta</b></li>
      </ul>
      <p class="xs muted">Ishonch xavf bahosidan alohida hisoblanadi. Yuqori baho avtomatik ravishda ishonchli degani emas.</p>
    </div>

    <div class="card panel">
      <div class="dq-head">
        <span class="section-label">Ma’lumot sifati</span>
        <span class="flow xs muted">Sifat <ArrowRight :size="11" /> ishonch</span>
      </div>
      <div class="dq-main num" :class="{ warn: low }">{{ num(risk.dq_score, 0) }}<small>/100</small></div>
      <div class="dims">
        <div v-for="d in dims" :key="d.key" class="dim">
          <span class="dim-label">{{ d.label }}</span>
          <span class="dim-bar"><i :class="{ warn: d.value < 60 }" :style="{ width: `${d.value}%` }" /></span>
          <span class="dim-val num">{{ num(d.value, 0) }}</span>
        </div>
      </div>
      <div v-if="low" class="notice notice-warn">
        <TriangleAlert :size="16" />
        Ma’lumot sifati past. Natijani ehtiyotkorlik bilan talqin qilish talab etiladi.
      </div>
    </div>
  </div>
</template>

<style scoped>
.trust { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr); gap: var(--gap); }
.panel { display: flex; flex-direction: column; gap: 12px; padding: 18px 20px; }
.conf-main { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.conf-val, .dq-main { font-size: 34px; font-weight: 720; color: var(--navy); letter-spacing: -0.03em; line-height: 1; }
.conf-val small, .dq-main small { font-size: 15px; font-weight: 560; color: var(--muted); margin-left: 2px; }
.dq-main.warn { color: var(--risk-medium-text); }
.conf-inputs { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
.conf-inputs li { display: flex; justify-content: space-between; font-size: var(--fs-md); color: var(--text-2); }
.conf-inputs b { color: var(--navy); font-weight: 620; }
.dq-head { display: flex; align-items: center; justify-content: space-between; }
.flow { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 999px; background: var(--surface-3); }
.dims { display: flex; flex-direction: column; gap: 6px; }
.dim { display: grid; grid-template-columns: 130px 1fr 30px; gap: 8px; align-items: center; font-size: var(--fs-sm); }
.dim-label { color: var(--text-2); }
.dim-bar { height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.dim-bar i { display: block; height: 100%; border-radius: 3px; background: var(--navy-3); }
.dim-bar i.warn { background: var(--risk-medium); }
.dim-val { text-align: right; font-weight: 600; color: var(--navy); }
</style>
