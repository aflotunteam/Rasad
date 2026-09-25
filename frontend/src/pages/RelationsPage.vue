<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RelationshipGraph from '@/components/charts/RelationshipGraph.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { subjectsApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useAuthStore } from '@/stores/auth'
import type { Relations, SubjectRow } from '@/types/api'
import { score as fmtScore } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const code = ref(typeof route.query.code === 'string' ? route.query.code : '')
const input = ref(code.value)
const depth = ref(2)
const data = ref<Relations | null>(null)
const error = ref<string | null>(null)
const loading = ref(false)
const suggestions = ref<SubjectRow[]>([])

async function load() {
  if (!code.value) return
  loading.value = true
  error.value = null
  try {
    data.value = await subjectsApi.relations(code.value, depth.value, 60)
  } catch (e) {
    data.value = null
    error.value = e instanceof ApiError ? e.message : 'Server xatosi'
  } finally {
    loading.value = false
  }
}

function go(c: string) {
  code.value = c.trim().toUpperCase().startsWith('SUB-') ? c.trim().toUpperCase() : `SUB-${c.trim().padStart(6, '0')}`
  input.value = code.value
  router.replace({ query: { code: code.value } })
}

watch([code, depth], load)
onMounted(async () => {
  // Tuzilmaviy xavf (R05) signali kuchli subyektlar — boshlash uchun tavsiya.
  const res = await subjectsApi.list({ risk_type: 'R05', level: 'attention', page_size: 8, region: auth.regionScope ?? undefined }).catch(() => null)
  suggestions.value = res?.items ?? []
  if (!code.value) go(suggestions.value[0]?.code ?? 'SUB-000125')
  else load()
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Aloqadorliklar</h1>
        <p class="page-sub">Subyektlar o‘rtasidagi ma’lum aloqalar: tur, kuch va xavf konteksti. Periferik past xavfli aloqalar yig‘ilgan holda ko‘rsatiladi.</p>
      </div>
    </div>
    <div class="card card-pad top">
      <form class="row" @submit.prevent="go(input)">
        <label class="srch"><Search :size="15" /><input v-model="input" class="input" placeholder="Ichki kod, masalan SUB-000125" aria-label="Ichki kod" /></label>
        <button class="btn btn-primary" type="submit">Ko‘rsatish</button>
        <RouterLink v-if="data" :to="{ name: 'subject', params: { code: data.center } }" class="btn">Kartani ochish</RouterLink>
      </form>
      <div v-if="suggestions.length" class="sugg">
        <span class="xs muted">Aloqadorlik xavfi (R05) kuzatilgan subyektlar:</span>
        <button v-for="s in suggestions" :key="s.code" class="chip" @click="go(s.code)">{{ s.code }} · {{ fmtScore(s.score) }}</button>
      </div>
    </div>
    <div class="card card-pad">
      <StateBlock v-if="error" kind="empty" :title="error" message="Boshqa ichki kodni kiriting." />
      <LoadingSkeleton v-else-if="!data || loading" block :height="560" />
      <RelationshipGraph v-else v-model:depth="depth" :data="data" :height="560" @open="(c) => router.push({ name: 'subject', params: { code: c } })" />
    </div>
  </div>
</template>

<style scoped>
.top { margin-bottom: var(--gap); display: flex; flex-direction: column; gap: 10px; }
.srch { position: relative; width: 340px; }
.srch svg { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: var(--muted); }
.srch .input { padding-left: 32px; }
.sugg { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.sugg .chip { cursor: pointer; }
.sugg .chip:hover { background: var(--blue-50); border-color: var(--blue-100); }
</style>
