<script setup lang="ts">
// Ishonch darajasi xavf rangidan ataylab farq qiladi: ko'k shkala va "signal" ustunchalari.
import type { Level } from '@/types/api'
import { CONFIDENCE_LABEL } from '@/utils/labels'

withDefaults(defineProps<{ level: Level; size?: 'sm' | 'md'; prefix?: boolean }>(), { size: 'md', prefix: false })
const bars = { high: 3, medium: 2, low: 1 }
</script>

<template>
  <span class="conf" :class="[`conf-${level}`, `conf-${size}`]" :aria-label="`Ishonch darajasi: ${CONFIDENCE_LABEL[level]}`">
    <span class="bars" aria-hidden="true">
      <i v-for="i in 3" :key="i" :class="{ on: i <= bars[level] }" :style="{ height: `${4 + i * 3}px` }" />
    </span>
    <span><template v-if="prefix">Ishonch: </template>{{ CONFIDENCE_LABEL[level] }}</span>
  </span>
</template>

<style scoped>
.conf {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 26px;
  padding: 0 9px;
  border: 1px solid var(--blue-100);
  border-radius: 7px;
  background: #f4f8ff;
  color: #24457a;
  font-size: var(--fs-sm);
  font-weight: 560;
  white-space: nowrap;
}

.conf-sm { height: 22px; padding: 0 7px; font-size: var(--fs-xs); }
.bars { display: inline-flex; align-items: flex-end; gap: 2px; height: 13px; }
.bars i { display: block; width: 3px; border-radius: 1px; background: #c7d6ee; }
.bars i.on { background: var(--blue); }
.conf-low { border-style: dashed; }
.conf-low .bars i.on { background: #7c93b8; }
</style>
