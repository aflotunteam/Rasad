<script setup lang="ts">
import { Lock } from 'lucide-vue-next'
import { onMounted, reactive, ref, watch } from 'vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import UiPagination from '@/components/ui/UiPagination.vue'
import { auditApi } from '@/services/api'
import type { AuditPage } from '@/types/api'
import { dateTime, num } from '@/utils/format'
import { AUDIT_ACTION_LABEL } from '@/utils/labels'

const f = reactive({ date_from: '', date_to: '', username: '', action: '' })
const page = ref(1)
const pageSize = ref(50)
const data = ref<AuditPage | null>(null)
const error = ref(false)

async function load() {
  error.value = false
  try {
    data.value = await auditApi.list({ ...f, page: page.value, page_size: pageSize.value })
  } catch {
    error.value = true
  }
}

function short(v: unknown): string {
  if (v === null || v === undefined) return '—'
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 90 ? s.slice(0, 90) + '…' : s
}

watch(f, () => {
  page.value = 1
  load()
})
watch([page, pageSize], load)
onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Audit</h1>
        <p class="page-sub">Kim, qachon, qanday amal bajargani. Jurnal faqat to‘ldiriladi: yozuvlarni o‘zgartirish yoki o‘chirish imkoni yo‘q.</p>
      </div>
      <span class="chip"><Lock :size="12" /> O‘zgartirilmaydigan jurnal</span>
    </div>

    <div class="card">
      <div class="filters">
        <label class="field"><span class="field-label">Sanadan</span><input v-model="f.date_from" type="date" class="input" /></label>
        <label class="field"><span class="field-label">Sanagacha</span><input v-model="f.date_to" type="date" class="input" /></label>
        <label class="field"><span class="field-label">Foydalanuvchi</span>
          <select v-model="f.username" class="select"><option value="">Barchasi</option><option v-for="u in data?.users" :key="u" :value="u">{{ u }}</option></select>
        </label>
        <label class="field"><span class="field-label">Amal</span>
          <select v-model="f.action" class="select"><option value="">Barchasi</option><option v-for="a in data?.actions" :key="a" :value="a">{{ AUDIT_ACTION_LABEL[a] ?? a }}</option></select>
        </label>
      </div>
      <StateBlock v-if="error" kind="server-error" @retry="load" />
      <div v-else-if="!data" class="card-pad"><LoadingSkeleton :lines="10" /></div>
      <StateBlock v-else-if="!data.items.length" kind="empty" />
      <div v-else class="table-wrap audit">
        <table class="table">
          <thead><tr><th>Kim</th><th>Qachon</th><th>Amal</th><th>Obyekt</th><th>Oldingi qiymat</th><th>Yangi qiymat</th><th>IP</th><th>Sessiya</th></tr></thead>
          <tbody>
            <tr v-for="r in data.items" :key="r.id">
              <td class="small"><b>{{ r.username }}</b></td>
              <td class="small num nowrap">{{ dateTime(r.at) }}</td>
              <td class="small">{{ AUDIT_ACTION_LABEL[r.action] ?? r.action }}</td>
              <td class="small">{{ r.object_type }}<span v-if="r.object_id" class="muted"> · {{ r.object_id }}</span></td>
              <td class="xs mono" :title="JSON.stringify(r.old_value)">{{ short(r.old_value) }}</td>
              <td class="xs mono" :title="JSON.stringify(r.new_value)">{{ short(r.new_value) }}</td>
              <td class="xs num muted">{{ r.ip ?? '—' }}</td>
              <td class="xs mono muted">{{ r.session_id ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <UiPagination v-if="data?.total" v-model:page="page" v-model:page-size="pageSize" :total="data.total" :sizes="[50, 100, 200]" />
    </div>
    <p class="xs muted foot">Jami yozuvlar: {{ num(data?.total ?? 0) }}</p>
  </div>
</template>

<style scoped>
.filters { display: grid; grid-template-columns: repeat(4, minmax(0, 220px)); gap: 12px; padding: 14px 16px; border-bottom: 1px solid var(--border); }
.filters .input, .filters .select { height: 34px; font-size: var(--fs-sm); }
.audit { max-height: calc(100vh - 330px); }
.mono { font-family: ui-monospace, Consolas, monospace; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.foot { margin-top: 8px; }
</style>
