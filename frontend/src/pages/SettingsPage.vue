<script setup lang="ts">
import { Info, Save } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { settingsApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useMetaStore } from '@/stores/meta'
import { useUiStore } from '@/stores/ui'
import type { SettingsAll } from '@/types/api'
import { dateTime, num } from '@/utils/format'

const meta = useMetaStore()
const ui = useUiStore()
const s = ref<SettingsAll | null>(null)
const low = ref(40)
const high = ref(70)
const saving = ref(false)
const error = ref(false)
const valid = computed(() => low.value >= 1 && high.value <= 99 && low.value < high.value)
const dirty = computed(() => s.value && (low.value !== s.value.risk_thresholds.low || high.value !== s.value.risk_thresholds.high))

async function load() {
  error.value = false
  try {
    s.value = await settingsApi.get()
    low.value = s.value.risk_thresholds.low
    high.value = s.value.risk_thresholds.high
  } catch {
    error.value = true
  }
}

async function save() {
  saving.value = true
  try {
    await settingsApi.setThresholds(low.value, high.value)
    ui.toast('Xavf chegaralari yangilandi. O‘zgarish audit jurnaliga yozildi.', 'success')
    await Promise.all([load(), meta.load(true)])
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Saqlab bo‘lmadi', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Sozlamalar</h1>
        <p class="page-sub">Xavf chegaralari, monitoring chegaralari va ma’lumotlarni saqlash siyosati.</p>
      </div>
    </div>

    <StateBlock v-if="error" kind="server-error" class="card" @retry="load" />
    <div v-else-if="!s" class="card card-pad"><LoadingSkeleton :lines="8" /></div>
    <div v-else class="set-grid">
      <section class="card card-pad th">
        <div class="card-title">Xavf chegaralari</div>
        <div class="notice notice-warn"><Info :size="16" /> {{ s.risk_thresholds.note }}</div>
        <div class="th-bar" aria-hidden="true">
          <i class="seg low" :style="{ width: `${low}%` }"><span>Past</span></i>
          <i class="seg med" :style="{ width: `${Math.max(0, high - low)}%` }"><span>O‘rta</span></i>
          <i class="seg high" :style="{ width: `${100 - high}%` }"><span>Yuqori</span></i>
        </div>
        <div class="th-inputs">
          <label class="field"><span class="field-label">O‘rta daraja boshlanishi</span><input v-model.number="low" type="number" min="1" max="98" class="input num" :disabled="!s.can_edit" /></label>
          <label class="field"><span class="field-label">Yuqori daraja boshlanishi</span><input v-model.number="high" type="number" min="2" max="99" class="input num" :disabled="!s.can_edit" /></label>
        </div>
        <div v-if="!valid" class="notice notice-danger small">Past chegara yuqori chegaradan kichik bo‘lishi kerak (1–99).</div>
        <div class="row">
          <span class="xs muted">Oxirgi o‘zgarish: {{ dateTime(s.risk_thresholds.updated_at) }} · {{ s.risk_thresholds.updated_by ?? '—' }}</span>
          <span class="spacer" />
          <button v-if="s.can_edit" class="btn btn-primary" :disabled="!valid || !dirty || saving" @click="save"><Save :size="15" /> Saqlash</button>
          <span v-else class="xs muted">Sizning rolingiz chegaralarni faqat ko‘rishi mumkin.</span>
        </div>
      </section>

      <section class="card card-pad">
        <div class="card-title">Model monitoringi chegaralari</div>
        <dl class="kv">
          <div><dt>Ma’lumot og‘ishi (PSI)</dt><dd class="num">{{ num(s.drift_thresholds?.psi, 2) }}</dd></div>
          <div><dt>Ekspert rad etish darajasi</dt><dd class="num">{{ num((s.drift_thresholds?.rejection_rate ?? 0) * 100, 0) }}%</dd></div>
          <div><dt>Ishonchning pasayishi</dt><dd class="num">{{ num((s.drift_thresholds?.confidence_drop ?? 0) * 100, 0) }} punkt</dd></div>
        </dl>
        <p class="xs muted">Chegaradan oshsa: «Modelni qayta tekshirish talab etiladi» ogohlantirishi chiqadi.</p>
      </section>

      <section class="card ret">
        <div class="card-head"><div class="card-title">Ma’lumotlarni saqlash siyosati</div></div>
        <table class="table">
          <thead><tr><th>Ma’lumot turi</th><th>Saqlash muddati</th><th>Arxiv muddati</th><th>O‘chirish tartibi</th></tr></thead>
          <tbody><tr v-for="r in s.retention_policy" :key="r.data_type"><td>{{ r.data_type }}</td><td>{{ r.retention }}</td><td>{{ r.archive }}</td><td>{{ r.deletion }}</td></tr></tbody>
        </table>
      </section>
    </div>
  </div>
</template>

<style scoped>
.set-grid { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: var(--gap); align-items: start; }
.th { display: flex; flex-direction: column; gap: 14px; }
.th-bar { display: flex; height: 30px; border-radius: 8px; overflow: hidden; font-size: var(--fs-xs); font-weight: 650; }
.seg { display: flex; align-items: center; justify-content: center; overflow: hidden; transition: width var(--t) var(--ease); }
.seg.low { background: var(--risk-low-bg); color: var(--risk-low-text); }
.seg.med { background: var(--risk-medium-bg); color: var(--risk-medium-text); }
.seg.high { background: var(--risk-high-bg); color: #b3302c; }
.th-inputs { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.kv { margin: 12px 0; display: flex; flex-direction: column; gap: 8px; }
.kv div { display: flex; justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
.kv dt { color: var(--muted); }
.kv dd { margin: 0; font-weight: 650; }
.ret { grid-column: 1 / -1; }
</style>
