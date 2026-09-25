<script setup lang="ts">
import { FlaskConical } from 'lucide-vue-next'

withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })
</script>

<template>
  <span class="synthetic" :class="{ compact }" title="Barcha ko‘rsatkichlar sun’iy yaratilgan va rasmiy statistika emas">
    <FlaskConical :size="compact ? 12 : 14" />
    <span>{{ compact ? 'Sintetik' : 'NAMOYISH MA’LUMOTLARI — SINTETIK' }}</span>
  </span>
</template>

<style scoped>
.synthetic {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 11px;
  border: 1px dashed #9cc0f5;
  border-radius: 999px;
  background: var(--blue-50);
  color: var(--blue-600);
  font-size: var(--fs-xs);
  font-weight: 650;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.synthetic.compact { height: 22px; padding: 0 8px; letter-spacing: 0.02em; }
</style>
