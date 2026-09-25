<script setup lang="ts">
import { HelpCircle } from 'lucide-vue-next'
import { computed } from 'vue'
import RiskBadge from './RiskBadge.vue'
import RiskTypeTag from './RiskTypeTag.vue'
import type { Risk } from '@/types/api'
import { score as fmtScore } from '@/utils/format'
import { LEVEL_HEX } from '@/utils/labels'

const props = defineProps<{ risk: Risk }>()
defineEmits<{ why: [] }>()
const pos = computed(() => Math.max(0, Math.min(100, props.risk.score)))
</script>

<template>
  <div class="rsp card">
    <div class="rsp-head">
      <span class="section-label">Xavf bahosi</span>
      <span class="chip">Sintetik namoyish natijasi</span>
    </div>
    <div class="rsp-main">
      <div class="rsp-score num" :style="{ color: LEVEL_HEX[risk.level] }">{{ fmtScore(risk.score) }}</div>
      <div class="rsp-of">/ 100</div>
      <RiskBadge :level="risk.level" class="rsp-badge" />
    </div>

    <div class="scale" aria-hidden="true">
      <div class="scale-track">
        <i class="seg seg-low" :style="{ width: `${risk.thresholds.low}%` }" />
        <i class="seg seg-med" :style="{ width: `${risk.thresholds.high - risk.thresholds.low}%` }" />
        <i class="seg seg-high" :style="{ width: `${100 - risk.thresholds.high}%` }" />
      </div>
      <div class="scale-marker" :style="{ left: `${pos}%` }" />
      <div class="scale-labels xs muted num">
        <span>0</span>
        <span :style="{ left: `${risk.thresholds.low}%` }">{{ risk.thresholds.low }}</span>
        <span :style="{ left: `${risk.thresholds.high}%` }">{{ risk.thresholds.high }}</span>
        <span>100</span>
      </div>
    </div>
    <p class="xs muted">Chegaralar MVP uchun shartli va Sozlamalarda o‘zgartiriladi. Ilmiy kalibrlanmagan.</p>

    <div class="rsp-types">
      <span class="xs muted">Asosiy xavf turi</span>
      <RiskTypeTag :code="risk.primary_risk_type" />
      <div v-if="risk.risk_types.length > 1" class="rsp-signals">
        <span class="xs muted">Kuzatilgan signallar:</span>
        <RiskTypeTag v-for="t in risk.risk_types" :key="t" :code="t" :show-name="false" />
      </div>
    </div>

    <button class="btn btn-dark why" @click="$emit('why')">
      <HelpCircle :size="18" />
      NEGA?
      <span class="why-sub">Bahoni shakllantirgan omillar</span>
    </button>
  </div>
</template>

<style scoped>
.rsp { display: flex; flex-direction: column; gap: 12px; padding: 18px 20px; }
.rsp-head { display: flex; align-items: center; justify-content: space-between; }
.rsp-main { display: flex; align-items: baseline; gap: 6px; }
.rsp-score { font-size: 56px; font-weight: 760; line-height: 1; letter-spacing: -0.04em; }
.rsp-of { font-size: 20px; font-weight: 600; color: var(--muted); }
.rsp-badge { margin-left: auto; align-self: center; }

.scale { position: relative; padding-top: 4px; }
.scale-track { display: flex; height: 8px; border-radius: 4px; overflow: hidden; }
.seg { display: block; height: 100%; }
.seg-low { background: #cfe9dc; }
.seg-med { background: #f3dfb0; }
.seg-high { background: #f1c4c2; }

.scale-marker {
  position: absolute;
  top: -1px;
  width: 4px;
  height: 18px;
  margin-left: -2px;
  border-radius: 2px;
  background: var(--navy);
  box-shadow: 0 0 0 2px #fff;
}

.scale-labels { position: relative; height: 16px; margin-top: 4px; }
.scale-labels span { position: absolute; transform: translateX(-50%); }
.scale-labels span:first-child { left: 0; transform: none; }
.scale-labels span:last-child { right: 0; transform: none; }

.rsp-types { display: flex; flex-direction: column; gap: 5px; padding-top: 10px; border-top: 1px solid var(--border); }
.rsp-signals { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.why {
  height: 52px;
  margin-top: 2px;
  justify-content: flex-start;
  padding: 0 16px;
  font-size: 16px;
  font-weight: 750;
  letter-spacing: 0.06em;
  border-radius: 12px;
}

.why-sub { margin-left: auto; font-size: var(--fs-sm); font-weight: 500; letter-spacing: 0; color: var(--on-dark-muted); }
</style>
