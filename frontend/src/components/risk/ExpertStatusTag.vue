<script setup lang="ts">
import { CircleDashed, CircleHelp, CircleSlash, CircleCheckBig, Send } from 'lucide-vue-next'
import type { ExpertStatus } from '@/types/api'
import { EXPERT_STATUS_LABEL } from '@/utils/labels'

defineProps<{ status: ExpertStatus }>()
const ICON = { pending: CircleDashed, confirmed: CircleCheckBig, rejected: CircleSlash, need_info: CircleHelp, sent_review: Send }
</script>

<template>
  <span class="estatus" :class="`es-${status}`">
    <component :is="ICON[status]" :size="13" />
    {{ EXPERT_STATUS_LABEL[status] }}
  </span>
</template>

<style scoped>
.estatus {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-2);
  font-size: var(--fs-sm);
  white-space: nowrap;
}

.es-pending { color: var(--muted); }
.es-confirmed svg { color: var(--navy); }
.es-rejected svg { color: var(--muted); }
.es-need_info svg,
.es-sent_review svg { color: var(--blue); }
</style>
