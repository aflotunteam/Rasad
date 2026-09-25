<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import RiskBadge from '@/components/risk/RiskBadge.vue'
import { subjectsApi } from '@/services/api'
import { useMetaStore } from '@/stores/meta'
import type { SubjectRow } from '@/types/api'

const router = useRouter()
const meta = useMetaStore()
const q = ref('')
const open = ref(false)
const results = ref<SubjectRow[]>([])
const active = ref(0)
const input = ref<HTMLInputElement | null>(null)
let timer: ReturnType<typeof setTimeout> | undefined

watch(q, (v) => {
  clearTimeout(timer)
  if (!v.trim()) {
    results.value = []
    return
  }
  timer = setTimeout(async () => {
    try {
      const page = await subjectsApi.list({ q: v.trim(), page_size: 6, sort: 'score' })
      results.value = page.items
      active.value = 0
      open.value = true
    } catch {
      results.value = []
    }
  }, 220)
})

function go(code: string) {
  open.value = false
  q.value = ''
  router.push({ name: 'subject', params: { code } })
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    active.value = Math.min(active.value + 1, results.value.length - 1)
    e.preventDefault()
  } else if (e.key === 'ArrowUp') {
    active.value = Math.max(active.value - 1, 0)
    e.preventDefault()
  } else if (e.key === 'Enter' && results.value[active.value]) {
    go(results.value[active.value].code)
  } else if (e.key === 'Escape') {
    open.value = false
  }
}

function shortcut(e: KeyboardEvent) {
  if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
    e.preventDefault()
    input.value?.focus()
  }
}
onMounted(() => document.addEventListener('keydown', shortcut))
onBeforeUnmount(() => document.removeEventListener('keydown', shortcut))
</script>

<template>
  <div class="gsearch" @focusout="(e) => !(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node) && (open = false)">
    <Search :size="16" class="gsearch-icon" />
    <input
      ref="input"
      v-model="q"
      class="gsearch-input"
      type="search"
      placeholder="Subyekt kodi bo‘yicha qidirish (masalan, 125)"
      aria-label="Global qidiruv"
      role="combobox"
      :aria-expanded="open"
      aria-controls="gsearch-list"
      @focus="results.length && (open = true)"
      @keydown="onKey"
    />
    <kbd class="gsearch-kbd">/</kbd>
    <div v-if="open" id="gsearch-list" class="gsearch-pop" role="listbox">
      <div v-if="!results.length" class="gsearch-empty">Mos subyekt topilmadi</div>
      <button
        v-for="(r, i) in results"
        :key="r.code"
        class="gsearch-item"
        :class="{ active: i === active }"
        role="option"
        :aria-selected="i === active"
        @mousedown.prevent="go(r.code)"
      >
        <span class="code">{{ r.code }}</span>
        <span class="muted small">{{ meta.regionShort(r.region_id) }} · {{ meta.sectorName(r.sector_id) }}</span>
        <span class="spacer" />
        <RiskBadge :score="r.score" :level="r.level" size="sm" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.gsearch { position: relative; width: min(440px, 36vw); }

.gsearch-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--muted);
}

.gsearch-input {
  width: 100%;
  height: 38px;
  padding: 0 38px 0 36px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-2);
  font-size: var(--fs-md);
  transition: border-color var(--t-fast), box-shadow var(--t-fast), background var(--t-fast);
}

.gsearch-input:focus { outline: none; background: #fff; border-color: var(--blue); box-shadow: var(--focus-ring); }

.gsearch-kbd {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  padding: 1px 6px;
  border: 1px solid var(--border-strong);
  border-radius: 5px;
  color: var(--muted);
  font-size: 11px;
  font-family: inherit;
}

.gsearch-pop {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  padding: 6px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
  z-index: 100;
}

.gsearch-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.gsearch-item.active,
.gsearch-item:hover { background: var(--surface-3); }
.gsearch-empty { padding: 10px; color: var(--muted); font-size: var(--fs-md); }
</style>
