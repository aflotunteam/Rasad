<script setup lang="ts">
// RASAD tahlil zanjiri (prompt §9): mahsulotning konseptual yuragi.
import {
  BadgeCheck,
  BrainCircuit,
  ChevronRight,
  DatabaseZap,
  Gauge,
  GitMerge,
  ListTree,
  SlidersHorizontal,
  Sparkles,
  UserCheck,
  type LucideIcon,
} from 'lucide-vue-next'
import type { ChainStep } from '@/types/api'
import { num } from '@/utils/format'

defineProps<{ steps: ChainStep[]; active?: string | null }>()

const ICON: Record<string, LucideIcon> = {
  quality: DatabaseZap,
  matching: GitMerge,
  features: ListTree,
  models: BrainCircuit,
  calibration: SlidersHorizontal,
  score: Gauge,
  confidence: BadgeCheck,
  factors: Sparkles,
  expert: UserCheck,
}
</script>

<template>
  <ol class="chain" aria-label="RASAD tahlil zanjiri">
    <li v-for="(s, i) in steps" :key="s.key" class="step" :class="{ active: active === s.key, human: s.key === 'expert' }">
      <div class="step-icon"><component :is="ICON[s.key]" :size="16" :stroke-width="1.9" /></div>
      <div class="step-label">{{ s.label }}</div>
      <div class="step-value num">{{ typeof s.value === 'number' ? num(s.value, Number.isInteger(s.value) ? 0 : 1) : s.value }}</div>
      <div class="step-unit">{{ s.unit }}</div>
      <ChevronRight v-if="i < steps.length - 1" class="step-arrow" :size="16" aria-hidden="true" />
    </li>
  </ol>
</template>

<style scoped>
.chain {
  display: grid;
  grid-template-columns: repeat(9, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.step {
  position: relative;
  padding: 11px 10px 10px;
  border: 1px solid var(--border);
  border-radius: 11px;
  background: var(--surface-2);
  min-width: 0;
  transition: border-color var(--t) var(--ease), background var(--t) var(--ease);
}

.step:hover { border-color: var(--blue-100); background: #fff; }
.step.active { border-color: var(--blue); background: var(--blue-50); }
.step.human { background: #eef2f8; border-color: #cfd9e8; }

.step-icon {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  margin-bottom: 8px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid var(--border);
  color: var(--blue);
}

.human .step-icon { color: var(--navy); }
.step-label { font-size: 11.5px; font-weight: 600; color: var(--text-2); line-height: 1.25; min-height: 29px; }
.step-value { margin-top: 5px; font-size: 17px; font-weight: 700; color: var(--navy); letter-spacing: -0.01em; }
.step-unit { font-size: 10.5px; color: var(--muted); line-height: 1.3; }

.step-arrow {
  position: absolute;
  right: -13px;
  top: 50%;
  transform: translateY(-50%);
  color: #a9b8ca;
  z-index: 1;
  background: var(--surface);
  border-radius: 50%;
}

@media (max-width: 1300px) {
  .chain { grid-template-columns: repeat(5, minmax(0, 1fr)); }
  .step-arrow { display: none; }
}
</style>
