<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed } from 'vue'
import { num } from '@/utils/format'

const props = defineProps<{ page: number; pageSize: number; total: number; sizes?: number[] }>()
const emit = defineEmits<{ 'update:page': [number]; 'update:pageSize': [number] }>()

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const from = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const to = computed(() => Math.min(props.total, props.page * props.pageSize))
</script>

<template>
  <div class="pager">
    <span class="muted small num">{{ num(from) }}–{{ num(to) }} / {{ num(total) }}</span>
    <div class="spacer" />
    <label v-if="sizes" class="row small muted">
      Sahifada
      <select
        class="select pager-size"
        :value="pageSize"
        @change="emit('update:pageSize', Number(($event.target as HTMLSelectElement).value))"
      >
        <option v-for="s in sizes" :key="s" :value="s">{{ s }}</option>
      </select>
    </label>
    <button class="btn btn-sm btn-icon" :disabled="page <= 1" aria-label="Oldingi sahifa" @click="emit('update:page', page - 1)">
      <ChevronLeft :size="16" />
    </button>
    <span class="small num">{{ page }} / {{ pages }}</span>
    <button class="btn btn-sm btn-icon" :disabled="page >= pages" aria-label="Keyingi sahifa" @click="emit('update:page', page + 1)">
      <ChevronRight :size="16" />
    </button>
  </div>
</template>

<style scoped>
.pager {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-top: 1px solid var(--border);
}

.pager-size { width: 74px; height: 30px; }
</style>
