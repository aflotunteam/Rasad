<script setup lang="ts">
import { CheckCircle2, CircleSlash, PlugZap, Sparkles, XCircle } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { aiApi } from '@/services/api'
import { ApiError } from '@/services/http'
import type { AiStatus, AiTestResult } from '@/types/api'
import { dateTime, num, relative } from '@/utils/format'

defineProps<{ canTest: boolean }>()
const status = ref<AiStatus | null>(null)
const error = ref<string | null>(null)
const testing = ref(false)
const test = ref<AiTestResult | null>(null)
const STATUS_LABEL = { ok: 'Tasdiqlandi', rejected: 'Rad etildi', error: 'Xato' }

async function load() {
  error.value = null
  try {
    status.value = await aiApi.status()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Holatni olib bo‘lmadi'
  }
}

async function runTest() {
  testing.value = true
  try {
    test.value = await aiApi.test()
    await load()
  } catch (e) {
    test.value = { ok: false, message: e instanceof ApiError ? e.message : 'Sinovni bajarib bo‘lmadi' }
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="card card-pad ai-panel">
    <div class="row">
      <div class="card-title"><Sparkles :size="18" class="title-icon" /> Sun’iy intellekt xizmati</div>
      <span class="spacer" />
      <button v-if="canTest" class="btn btn-sm" :disabled="testing" @click="runTest">
        <PlugZap :size="14" /> {{ testing ? 'Tekshirilmoqda…' : 'Ulanishni tekshirish' }}
      </button>
    </div>

    <div v-if="error" class="notice notice-danger small">{{ error }}</div>
    <LoadingSkeleton v-else-if="!status" :lines="4" />
    <template v-else>
      <div class="mode" :class="status.mode">
        <component :is="status.mode === 'ai' ? CheckCircle2 : CircleSlash" :size="18" />
        <div>
          <b>{{ status.mode === 'ai' ? `Faol: ${status.model_label}` : 'Shablon rejimi' }}</b>
          <div class="small">
            <template v-if="status.mode === 'ai'">SI izohlari Claude modeli bilan yoziladi va har bir son tekshiriladi.</template>
            <template v-else-if="!status.enabled">SI xizmati sozlamalarda o‘chirilgan (AI_ENABLED=false).</template>
            <template v-else>API kaliti o‘rnatilmagan. Izohlar hisoblangan natijalardan shablon asosida tuziladi.</template>
          </div>
        </div>
      </div>

      <div v-if="test" class="notice small" :class="test.ok ? 'notice-info' : 'notice-danger'">
        <component :is="test.ok ? CheckCircle2 : XCircle" :size="15" />
        <span>{{ test.message }}<template v-if="test.ok"> · {{ test.display_name ?? test.model }} · {{ test.latency_ms }} ms</template></span>
      </div>

      <dl class="kv">
        <div><dt>Model</dt><dd class="mono">{{ status.model }}</dd></div>
        <div><dt>Effort</dt><dd>{{ status.effort }}</dd></div>
        <div><dt>Kutish chegarasi</dt><dd class="num">{{ status.timeout_seconds }} s</dd></div>
        <div><dt>Prompt versiyasi</dt><dd>{{ status.prompt_version }}</dd></div>
        <div><dt>Tasdiqlangan izohlar</dt><dd class="num">{{ num(status.totals.ok) }}</dd></div>
        <div><dt>Rad etilgan / xato</dt><dd class="num">{{ num(status.totals.rejected) }} / {{ num(status.totals.error) }}</dd></div>
        <div><dt>Tokenlar (kirish / chiqish)</dt><dd class="num">{{ num(status.totals.input_tokens) }} / {{ num(status.totals.output_tokens) }}</dd></div>
        <div><dt>O‘rtacha javob vaqti</dt><dd class="num">{{ status.session.avg_latency_ms ? `${num(status.session.avg_latency_ms)} ms` : '—' }}</dd></div>
      </dl>

      <div v-if="status.session.last_error" class="notice notice-warn small">
        Oxirgi xato ({{ relative(status.session.last_error_at) }}): {{ status.session.last_error }}
      </div>

      <div v-if="status.recent.length">
        <div class="section-label">Oxirgi chaqiruvlar</div>
        <table class="table recent">
          <thead><tr><th>Subyekt</th><th>Natija</th><th class="right">Tokenlar</th><th class="right">Vaqt</th><th>Qachon</th></tr></thead>
          <tbody>
            <tr v-for="(r, i) in status.recent" :key="i" :title="r.reason ?? ''">
              <td class="code">{{ r.subject_code }}</td>
              <td><span class="st" :class="`st-${r.status}`">{{ STATUS_LABEL[r.status] }}</span></td>
              <td class="right num small">{{ num(r.input_tokens + r.output_tokens) }}</td>
              <td class="right num small">{{ num(r.latency_ms) }} ms</td>
              <td class="small muted">{{ dateTime(r.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="xs muted">
        Kalit faqat serverdagi <code>.env</code> faylida saqlanadi (<code>ANTHROPIC_API_KEY</code>) va brauzerga hech qachon yuborilmaydi.
        Kalit bo‘lmasa yoki model javobi tekshiruvdan o‘tmasa, platforma shablon izohi bilan ishlashda davom etadi.
      </p>
    </template>
  </section>
</template>

<style scoped>
.ai-panel { display: flex; flex-direction: column; gap: 14px; grid-column: 1 / -1; }
.card-title { display: inline-flex; align-items: center; gap: 8px; }
.title-icon { color: var(--blue); }
.mode { display: flex; gap: 12px; align-items: flex-start; padding: 12px 14px; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-2); }
.mode.ai { background: var(--blue-50); border-color: var(--blue-100); }
.mode.ai svg { color: var(--blue); }
.mode.template svg { color: var(--muted); }
.kv { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px 16px; margin: 0; }
.kv dt { font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
.kv dd { margin: 2px 0 0; font-weight: 620; }
.mono { font-family: ui-monospace, Consolas, monospace; font-size: 13px; }
.recent { margin-top: 6px; }
.st { display: inline-flex; padding: 1px 8px; border-radius: 999px; font-size: var(--fs-xs); font-weight: 600; background: var(--surface-3); }
.st-ok { background: var(--blue-50); color: var(--blue-600); }
.st-rejected { background: var(--risk-medium-bg); color: var(--risk-medium-text); }
.st-error { background: var(--risk-high-bg); color: #b3302c; }
</style>
