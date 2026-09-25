<script setup lang="ts">
import { Bookmark, BookmarkPlus, RotateCcw, Search, Trash2 } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { EXPERT_STATUS_LABEL } from '@/utils/labels'

export interface Filters {
  region: string
  sector: string
  level: string
  risk_type: string
  expert_status: string
  dq: string
  confidence: string
  q: string
}

const model = defineModel<Filters>({ required: true })
const emit = defineEmits<{ reset: [] }>()
const meta = useMetaStore()
const auth = useAuthStore()

const SAVED_KEY = 'rasad.saved-filters'
interface Saved {
  name: string
  filters: Filters
}

function readSaved(): Saved[] {
  try {
    return JSON.parse(localStorage.getItem(SAVED_KEY) ?? '[]')
  } catch {
    return []
  }
}

const saved = ref<Saved[]>(readSaved())
const naming = ref(false)
const newName = ref('')

function persist() {
  try {
    localStorage.setItem(SAVED_KEY, JSON.stringify(saved.value))
  } catch {
    /* saqlab bo'lmasa, filtr faqat joriy sessiyada qoladi */
  }
}

function save() {
  const name = newName.value.trim()
  if (!name) return
  saved.value = [...saved.value.filter((s) => s.name !== name), { name, filters: { ...model.value } }]
  persist()
  naming.value = false
  newName.value = ''
}

function apply(s: Saved) {
  model.value = { ...s.filters, region: auth.regionScope ?? s.filters.region }
}

function remove(name: string) {
  saved.value = saved.value.filter((s) => s.name !== name)
  persist()
}

const active = computed(() => Object.entries(model.value).filter(([k, v]) => v && !(k === 'region' && auth.regionScope)).length)

function set<K extends keyof Filters>(key: K, value: string) {
  model.value = { ...model.value, [key]: value }
}
</script>

<template>
  <div class="filters">
    <div class="f-row">
      <label class="f-search">
        <Search :size="15" />
        <input
          class="input"
          :value="model.q"
          placeholder="Ichki kod bo‘yicha qidirish"
          aria-label="Ichki kod bo‘yicha qidirish"
          @input="set('q', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <select class="select" aria-label="Hudud" :value="model.region" :disabled="!!auth.regionScope" @change="set('region', ($event.target as HTMLSelectElement).value)">
        <option value="">Barcha hududlar</option>
        <option v-for="r in meta.meta?.regions" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
      <select class="select" aria-label="Faoliyat turi" :value="model.sector" @change="set('sector', ($event.target as HTMLSelectElement).value)">
        <option value="">Barcha faoliyat turlari</option>
        <option v-for="s in meta.meta?.sectors" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <select class="select" aria-label="Xavf darajasi" :value="model.level" @change="set('level', ($event.target as HTMLSelectElement).value)">
        <option value="">Har qanday daraja</option>
        <option value="high">Yuqori</option>
        <option value="medium">O‘rta</option>
        <option value="attention">O‘rta va yuqori</option>
        <option value="low">Past</option>
      </select>
      <select class="select" aria-label="Xavf turi" :value="model.risk_type" @change="set('risk_type', ($event.target as HTMLSelectElement).value)">
        <option value="">Har qanday xavf turi</option>
        <option v-for="t in meta.meta?.risk_types" :key="t.code" :value="t.code">{{ t.code }} — {{ t.name }}</option>
      </select>
    </div>
    <div class="f-row">
      <select class="select" aria-label="Davr" disabled title="MVP da bitta tahlil davri mavjud">
        <option>Davr: joriy ({{ meta.meta?.period?.data_version }})</option>
      </select>
      <select class="select" aria-label="Ekspert holati" :value="model.expert_status" @change="set('expert_status', ($event.target as HTMLSelectElement).value)">
        <option value="">Har qanday ekspert holati</option>
        <option v-for="(label, key) in EXPERT_STATUS_LABEL" :key="key" :value="key">{{ label }}</option>
      </select>
      <select class="select" aria-label="Ma’lumot sifati" :value="model.dq" @change="set('dq', ($event.target as HTMLSelectElement).value)">
        <option value="">Har qanday ma’lumot sifati</option>
        <option value="high">Yuqori (≥ 80)</option>
        <option value="medium">O‘rta (60–79)</option>
        <option value="low">Past (&lt; 60)</option>
      </select>
      <select class="select" aria-label="Ishonch darajasi" :value="model.confidence" @change="set('confidence', ($event.target as HTMLSelectElement).value)">
        <option value="">Har qanday ishonch</option>
        <option value="high">Ishonch: yuqori</option>
        <option value="medium">Ishonch: o‘rta</option>
        <option value="low">Ishonch: past</option>
      </select>
      <div class="f-actions">
        <button class="btn btn-sm" :disabled="!active" @click="emit('reset')"><RotateCcw :size="14" /> Tozalash</button>
        <template v-if="naming">
          <input v-model="newName" class="input f-name" placeholder="Filtr nomi" aria-label="Filtr nomi" @keydown.enter="save" @keydown.esc="naming = false" />
          <button class="btn btn-sm btn-primary" :disabled="!newName.trim()" @click="save">Saqlash</button>
        </template>
        <button v-else class="btn btn-sm" :disabled="!active" @click="naming = true"><BookmarkPlus :size="14" /> Filtrni saqlash</button>
      </div>
    </div>
    <div v-if="saved.length" class="f-saved">
      <span class="xs muted">Saqlangan filtrlar:</span>
      <span v-for="s in saved" :key="s.name" class="saved-chip">
        <button class="saved-apply" @click="apply(s)"><Bookmark :size="12" /> {{ s.name }}</button>
        <button class="saved-del" :aria-label="`${s.name} filtrini o‘chirish`" @click="remove(s.name)"><Trash2 :size="12" /></button>
      </span>
    </div>
  </div>
</template>

<style scoped>
.filters { display: flex; flex-direction: column; gap: 10px; padding: 14px 16px; border-bottom: 1px solid var(--border); }
.f-row { display: grid; grid-template-columns: 1.3fr repeat(4, minmax(0, 1fr)); gap: 10px; align-items: center; }
.f-row:nth-child(2) { grid-template-columns: repeat(4, minmax(0, 1fr)) auto; }
.f-row .select, .f-row .input { height: 34px; font-size: var(--fs-sm); }
.f-search { position: relative; }
.f-search svg { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: var(--muted); }
.f-search .input { padding-left: 32px; }
.f-actions { display: flex; gap: 6px; justify-content: flex-end; }
.f-name { width: 150px; height: 30px !important; }
.f-saved { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }

.saved-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--blue-100);
  border-radius: 999px;
  background: var(--blue-50);
  overflow: hidden;
}

.saved-chip button { display: inline-flex; align-items: center; gap: 4px; border: 0; background: transparent; color: var(--blue-600); cursor: pointer; font-size: var(--fs-xs); font-weight: 560; }
.saved-apply { padding: 3px 6px 3px 9px; }
.saved-del { padding: 3px 8px 3px 4px; opacity: 0.6; }
.saved-del:hover { opacity: 1; }
</style>
