<script setup lang="ts">
// Xavf darajasi faqat rang bilan emas: rang + ikon + matn (TZ §39).
import { CircleCheck, OctagonAlert, TriangleAlert } from 'lucide-vue-next'
import { computed } from 'vue'
import type { Level } from '@/types/api'
import { score as fmtScore } from '@/utils/format'
import { LEVEL_LABEL } from '@/utils/labels'

const props = withDefaults(defineProps<{ level: Level; score?: number | null; size?: 'sm' | 'md'; showLabel?: boolean }>(), {
  size: 'md',
  showLabel: true,
  score: null,
})
const icon = computed(() => ({ high: OctagonAlert, medium: TriangleAlert, low: CircleCheck })[props.level])
</script>

<template>
  <span class="risk" :class="[`risk-${level}`, `risk-${size}`]" :aria-label="`Xavf: ${LEVEL_LABEL[level]}${score !== null ? `, ${fmtScore(score)} ball` : ''}`">
    <component :is="icon" :size="size === 'sm' ? 13 : 14" :stroke-width="2.2" />
    <span v-if="score !== null" class="risk-score num">{{ fmtScore(score) }}</span>
    <span v-if="showLabel" class="risk-label">{{ LEVEL_LABEL[level] }}</span>
  </span>
</template>

<style scoped>
.risk {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 26px;
  padding: 0 9px 0 7px;
  border: 1px solid;
  border-radius: 7px;
  font-size: var(--fs-sm);
  font-weight: 600;
  white-space: nowrap;
}

.risk-sm { height: 22px; padding: 0 7px 0 6px; font-size: var(--fs-xs); gap: 4px; }
.risk-score { font-weight: 700; }
.risk-label { font-weight: 560; }
.risk-score + .risk-label::before { content: '·'; margin-right: 4px; opacity: 0.6; }
.risk-high { color: #b3302c; background: var(--risk-high-bg); border-color: var(--risk-high-border); }
.risk-high svg { color: var(--risk-high); }
.risk-medium { color: var(--risk-medium-text); background: var(--risk-medium-bg); border-color: var(--risk-medium-border); }
.risk-medium svg { color: var(--risk-medium); }
.risk-low { color: var(--risk-low-text); background: var(--risk-low-bg); border-color: var(--risk-low-border); }
.risk-low svg { color: var(--risk-low); }
</style>
