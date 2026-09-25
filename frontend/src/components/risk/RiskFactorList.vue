<script setup lang="ts">
// Xavf sabablari (TZ §16): omil, joriy qiymat, kutilgan oraliq, og'ish, ta'sir, manba.
import { computed } from 'vue'
import RiskTypeTag from './RiskTypeTag.vue'
import type { Factor } from '@/types/api'
import { signed, withUnit } from '@/utils/format'
import { LEVEL_LABEL } from '@/utils/labels'

const props = withDefaults(defineProps<{ factors: Factor[]; score: number; limit?: number; detailed?: boolean }>(), {
  detailed: true,
})
const list = computed(() => props.factors.filter((f) => f.impact > 0.05).slice(0, props.limit ?? 99))
const max = computed(() => Math.max(1, ...list.value.map((f) => f.impact)))
</script>

<template>
  <ol class="factors">
    <li v-for="f in list" :key="f.feature + f.rank" class="factor">
      <div class="f-head">
        <span class="f-rank num">{{ f.rank }}</span>
        <span class="f-name">{{ f.factor }}</span>
        <span class="f-impact num">{{ signed(f.impact, 1) }} ball</span>
      </div>
      <div class="f-bar" :aria-label="`Xavf bahosiga ta’siri ${signed(f.impact, 1)} ball`">
        <i :style="{ width: `${(f.impact / max) * 100}%` }" :class="`dev-${f.deviation}`" />
      </div>
      <dl v-if="detailed" class="f-grid">
        <div><dt>Joriy</dt><dd class="num">{{ withUnit(f.current_value, f.unit) }}</dd></div>
        <div><dt>Kutilgan oraliq</dt><dd class="num">{{ withUnit(f.baseline_low, f.unit) }} … {{ withUnit(f.baseline_high, f.unit) }}</dd></div>
        <div><dt>Og‘ish</dt><dd>{{ LEVEL_LABEL[f.deviation] }}</dd></div>
        <div><dt>Xavf turi</dt><dd><RiskTypeTag :code="f.risk_type" :show-name="false" /></dd></div>
        <div class="f-src"><dt>Manba</dt><dd><code>{{ f.source }}</code></dd></div>
      </dl>
    </li>
  </ol>
</template>

<style scoped>
.factors { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 12px; }
.factor { padding: 12px 14px; border: 1px solid var(--border); border-radius: 11px; background: var(--surface); }
.f-head { display: flex; align-items: center; gap: 10px; }

.f-rank {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--navy);
  color: #fff;
  font-size: 11.5px;
  font-weight: 700;
}

.f-name { flex: 1; font-weight: 620; color: var(--navy); }
.f-impact { font-weight: 700; color: var(--navy); }
.f-bar { height: 8px; margin: 9px 0 2px; border-radius: 4px; background: var(--surface-3); overflow: hidden; }
.f-bar i { display: block; height: 100%; border-radius: 4px; background: var(--navy-3); }
.f-bar i.dev-high { background: linear-gradient(90deg, #1c3760, #216df3); }
.f-bar i.dev-medium { background: #6f9be8; }
.f-bar i.dev-low { background: #b9cff3; }

.f-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  gap: 8px 14px;
  margin: 10px 0 0;
}

.f-grid dt { font-size: 10.5px; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); }
.f-grid dd { margin: 2px 0 0; font-size: var(--fs-md); font-weight: 560; color: var(--text); }
.f-src { grid-column: 1 / -1; }
.f-src code { font-size: 12px; color: var(--muted); }
</style>
