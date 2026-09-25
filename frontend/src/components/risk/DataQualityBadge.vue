<script setup lang="ts">
// Ma'lumot sifati: neytral ko'rsatkich, past bo'lsa ogohlantiruvchi ikon bilan.
import { Database, DatabaseBackup } from 'lucide-vue-next'
import { computed } from 'vue'
import { num } from '@/utils/format'

const props = withDefaults(defineProps<{ value: number; size?: 'sm' | 'md'; lowThreshold?: number }>(), {
  size: 'md',
  lowThreshold: 60,
})
const low = computed(() => props.value < props.lowThreshold)
</script>

<template>
  <span class="dq" :class="[`dq-${size}`, { 'dq-low': low }]" :aria-label="`Ma’lumot sifati ${num(value, 0)} / 100${low ? ', past' : ''}`">
    <component :is="low ? DatabaseBackup : Database" :size="size === 'sm' ? 12 : 14" />
    <span class="num">{{ num(value, 0) }}</span><span class="dq-of">/100</span>
    <span class="dq-bar" aria-hidden="true"><i :style="{ width: `${Math.max(4, Math.min(100, value))}%` }" /></span>
  </span>
</template>

<style scoped>
.dq {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-2);
  font-size: var(--fs-sm);
  font-weight: 600;
  white-space: nowrap;
}

.dq svg { color: var(--muted); }
.dq-of { color: var(--muted-2); font-weight: 500; margin-left: -3px; }
.dq-bar { width: 40px; height: 4px; margin-left: 3px; border-radius: 2px; background: var(--surface-3); overflow: hidden; }
.dq-bar i { display: block; height: 100%; background: var(--navy-3); border-radius: 2px; }
.dq-low { color: var(--risk-medium-text); }
.dq-low svg { color: var(--risk-medium); }
.dq-low .dq-bar i { background: var(--risk-medium); }
.dq-sm { font-size: var(--fs-xs); }
.dq-sm .dq-bar { width: 30px; }
</style>
