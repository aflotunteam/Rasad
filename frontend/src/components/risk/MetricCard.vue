<script setup lang="ts">
import type { LucideIcon } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    label: string
    value: string
    icon: LucideIcon
    hint?: string
    tone?: 'navy' | 'blue' | 'cyan' | 'high' | 'medium' | 'neutral'
    to?: string | object
  }>(),
  { tone: 'navy' },
)
</script>

<template>
  <component :is="to ? 'RouterLink' : 'div'" :to="to" class="metric card" :class="{ link: !!to }">
    <div class="metric-top">
      <div class="metric-icon" :class="`tone-${tone}`"><component :is="icon" :size="16" :stroke-width="1.9" /></div>
      <div class="metric-label">{{ label }}</div>
    </div>
    <div class="metric-value num" :title="value">{{ value }}</div>
    <div v-if="hint" class="metric-hint" :title="hint">{{ hint }}</div>
  </component>
</template>

<style scoped>
.metric {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 15px 13px;
  min-width: 0;
  color: inherit;
  text-decoration: none;
  transition: box-shadow var(--t) var(--ease), border-color var(--t) var(--ease), transform var(--t) var(--ease);
}

.metric.link:hover { border-color: var(--blue-100); box-shadow: var(--shadow-md); text-decoration: none; }

.metric-icon {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 8px;
}

.tone-navy { background: #e9eef6; color: var(--navy); }
.tone-blue { background: var(--blue-50); color: var(--blue); }
.tone-cyan { background: var(--cyan-50); color: #0b87bd; }
.tone-high { background: var(--risk-high-bg); color: var(--risk-high); }
.tone-medium { background: var(--risk-medium-bg); color: var(--risk-medium-text); }
.tone-neutral { background: var(--surface-3); color: var(--muted); }

.metric-top { display: flex; align-items: center; gap: 9px; min-height: 32px; }
.metric-label { font-size: var(--fs-sm); color: var(--muted); line-height: 1.25; }

.metric-value {
  font-size: 23px;
  font-weight: 700;
  color: var(--navy);
  letter-spacing: -0.02em;
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metric-hint { margin-top: -3px; font-size: var(--fs-xs); color: var(--muted-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
