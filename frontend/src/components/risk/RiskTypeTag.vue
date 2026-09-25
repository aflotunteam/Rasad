<script setup lang="ts">
import { computed } from 'vue'
import { useMetaStore } from '@/stores/meta'
import { RISK_TYPE_ICON } from '@/utils/icons'

const props = withDefaults(defineProps<{ code: string; showName?: boolean }>(), { showName: true })
const meta = useMetaStore()
const type = computed(() => meta.riskType(props.code))
</script>

<template>
  <span class="rtype" :title="type ? `${type.code} — ${type.name}. ${type.description}` : code">
    <component :is="RISK_TYPE_ICON[code]" :size="13" />
    <span class="rtype-code">{{ code }}</span>
    <span v-if="showName && type" class="rtype-name">{{ type.name }}</span>
  </span>
</template>

<style scoped>
.rtype {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  color: var(--text-2);
  font-size: var(--fs-sm);
  white-space: nowrap;
}

.rtype svg { flex-shrink: 0; color: var(--blue); }
.rtype-code { font-weight: 650; color: var(--navy); }
.rtype-name { overflow: hidden; text-overflow: ellipsis; }
</style>
