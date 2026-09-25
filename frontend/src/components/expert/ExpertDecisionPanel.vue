<script setup lang="ts">
// Ekspert qarori (prompt §20): avtomatik natija hech qachon yakuniy emas.
import { CircleCheckBig, CircleHelp, CircleSlash, Scale, Send, type LucideIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { decisionsApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import type { Decision, DecisionType } from '@/types/api'
import { dateTime, score as fmtScore } from '@/utils/format'
import { DECISION_HINT, DECISION_LABEL } from '@/utils/labels'

const props = defineProps<{ code: string; decisions: Decision[] }>()
const emit = defineEmits<{ saved: [Decision] }>()
const auth = useAuthStore()
const ui = useUiStore()

const OPTIONS: { key: DecisionType; icon: LucideIcon }[] = [
  { key: 'confirmed', icon: CircleCheckBig },
  { key: 'rejected', icon: CircleSlash },
  { key: 'need_info', icon: CircleHelp },
  { key: 'sent_review', icon: Send },
]

const choice = ref<DecisionType | null>(null)
const comment = ref('')
const saving = ref(false)
const error = ref<string | null>(null)
const canWrite = computed(() => auth.can('decisions.write'))
const valid = computed(() => !!choice.value && comment.value.trim().length >= 10)

async function submit() {
  if (!valid.value || !choice.value) return
  saving.value = true
  error.value = null
  try {
    const d = await decisionsApi.create(props.code, choice.value, comment.value.trim())
    emit('saved', d)
    ui.toast('Ekspert qarori saqlandi va audit jurnaliga yozildi', 'success')
    window.dispatchEvent(new Event('rasad:alerts-changed'))
    choice.value = null
    comment.value = ''
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Qarorni saqlab bo‘lmadi'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="edp">
    <div class="disclaimer">
      <Scale :size="16" />
      <span>Mazkur baho avtomatik tahlil natijasi bo‘lib, yakuniy huquqiy xulosa hisoblanmaydi.</span>
    </div>

    <form v-if="canWrite" class="edp-form" @submit.prevent="submit">
      <div class="options" role="radiogroup" aria-label="Ekspert qarori">
        <button
          v-for="o in OPTIONS"
          :key="o.key"
          type="button"
          role="radio"
          :aria-checked="choice === o.key"
          class="opt"
          :class="{ active: choice === o.key }"
          @click="choice = o.key"
        >
          <component :is="o.icon" :size="16" />
          <span class="opt-label">{{ DECISION_LABEL[o.key] }}</span>
          <span class="opt-hint">{{ DECISION_HINT[o.key] }}</span>
        </button>
      </div>
      <label class="field">
        <span class="field-label">Izoh <span class="muted">(majburiy, kamida 10 belgi)</span></span>
        <textarea v-model="comment" class="textarea" maxlength="2000" placeholder="Qaror asoslarini qisqacha yozing" />
      </label>
      <div v-if="error" class="notice notice-danger" role="alert">{{ error }}</div>
      <div class="row">
        <span class="xs muted">Qaror foydalanuvchi, vaqt va izoh bilan saqlanadi.</span>
        <span class="spacer" />
        <button class="btn btn-primary" type="submit" :disabled="!valid || saving">{{ saving ? 'Saqlanmoqda…' : 'Qarorni saqlash' }}</button>
      </div>
    </form>
    <div v-else class="notice">Sizning rolingiz ekspert qarorini qabul qilish huquqiga ega emas. Qarorlar tarixi quyida.</div>

    <div class="timeline">
      <div class="section-label">Qarorlar tarixi</div>
      <div v-if="!decisions.length" class="muted small tl-empty">Ekspert qarori hali qabul qilinmagan.</div>
      <ol v-else>
        <li v-for="d in decisions" :key="d.id" class="tl-item">
          <span class="tl-dot" :class="`tl-${d.decision}`" />
          <div class="tl-body">
            <div class="row">
              <b>{{ DECISION_LABEL[d.decision] }}</b>
              <span class="spacer" />
              <span class="xs muted num">{{ dateTime(d.created_at) }}</span>
            </div>
            <div class="tl-comment">{{ d.comment }}</div>
            <div class="xs muted">{{ d.user.full_name }} · qaror vaqtidagi baho {{ fmtScore(d.score_at_decision) }} · {{ d.model_version }}</div>
          </div>
        </li>
      </ol>
    </div>
  </div>
</template>

<style scoped>
.edp { display: flex; flex-direction: column; gap: 14px; }

.disclaimer {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: var(--radius);
  background: var(--navy);
  color: #dbe5f3;
  font-size: var(--fs-sm);
  line-height: 1.45;
}

.disclaimer svg { flex-shrink: 0; margin-top: 1px; color: var(--cyan); }
.edp-form { display: flex; flex-direction: column; gap: 12px; }
.options { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

.opt {
  display: grid;
  grid-template-columns: 18px 1fr;
  grid-template-rows: auto auto;
  column-gap: 8px;
  align-items: center;
  padding: 10px 11px;
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color var(--t-fast), background var(--t-fast), box-shadow var(--t-fast);
}

.opt svg { grid-row: 1 / 3; color: var(--muted); }
.opt-label { font-size: var(--fs-md); font-weight: 620; color: var(--navy); }
.opt-hint { font-size: var(--fs-xs); color: var(--muted); }
.opt:hover { border-color: var(--blue-100); background: var(--surface-2); }
.opt.active { border-color: var(--blue); background: var(--blue-50); box-shadow: 0 0 0 1px var(--blue); }
.opt.active svg { color: var(--blue); }
.timeline ol { margin: 8px 0 0; padding: 0; list-style: none; }
.tl-empty { margin-top: 6px; }
.tl-item { position: relative; display: flex; gap: 12px; padding: 0 0 14px 2px; }
.tl-item:not(:last-child)::before { content: ''; position: absolute; left: 7px; top: 16px; bottom: 0; width: 2px; background: var(--border); }
.tl-dot { flex-shrink: 0; width: 12px; height: 12px; margin-top: 3px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 0 0 2px var(--muted); background: var(--muted); }
.tl-confirmed { background: var(--navy); box-shadow: 0 0 0 2px var(--navy); }
.tl-sent_review, .tl-need_info { background: var(--blue); box-shadow: 0 0 0 2px var(--blue); }
.tl-body { flex: 1; display: flex; flex-direction: column; gap: 3px; font-size: var(--fs-md); }
.tl-comment { color: var(--text-2); }
</style>
