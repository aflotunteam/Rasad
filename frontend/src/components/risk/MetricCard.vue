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
    <div class="metric-icon" :class="`tone-${tone}`"><component :is="icon" :size="18" :stroke-width="1.9" /></div>
    <div class="metric-main">
      <div class="metric-label">{{ label }}</div>
      <div class="metric-value num">{{ value }}</div>
      <div v-if="hint" class="metric-hint">{{ hint }}</div>
    </div>
  </component>
</template>

<style scoped>
.metric {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 15px 16px;
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
  width: 38px;
  height: 38px;
  border-radius: 10px;
}

.tone-navy { background: #e9eef6; color: var(--navy); }
.tone-blue { background: var(--blue-50); color: var(--blue); }
.tone-cyan { background: var(--cyan-50); color: #0b87bd; }
.tone-high { background: var(--risk-high-bg); color: var(--risk-high); }
.tone-medium { background: var(--risk-medium-bg); color: var(--risk-medium-text); }
.tone-neutral { background: var(--surface-3); color: var(--muted); }

.metric-main { min-width: 0; }
.metric-label { font-size: var(--fs-sm); color: var(--muted); line-height: 1.3; }

.metric-value {
  margin-top: 4px;
  font-size: 24px;
  font-weight: 700;
  color: var(--navy);
  letter-spacing: -0.02em;
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metric-hint { margin-top: 4px; font-size: var(--fs-xs); color: var(--muted-2); }
</style>
