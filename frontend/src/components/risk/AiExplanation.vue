<script setup lang="ts">
import { FileText, RefreshCw, ShieldCheck, Sparkles, TriangleAlert } from 'lucide-vue-next'
import { computed } from 'vue'
import type { Explanation } from '@/types/api'
import { dateTime } from '@/utils/format'

const props = withDefaults(defineProps<{ explanation: Explanation; canRegenerate?: boolean; busy?: boolean }>(), {
  canRegenerate: false,
  busy: false,
})
defineEmits<{ regenerate: [] }>()

const isAi = computed(() => props.explanation.source === 'ai')
// Kalit o'rnatilmagani odatiy holat; model javobi rad etilgani yoki xato esa foydalanuvchiga aytiladi.
const warn = computed(() => !isAi.value && ['rejected', 'error'].includes(props.explanation.fallback_code ?? ''))
</script>

<template>
  <div class="ai">
    <div class="ai-head">
      <span v-if="isAi" class="ai-badge"><Sparkles :size="14" /> {{ explanation.model_label }}</span>
      <span v-else class="ai-badge tpl"><FileText :size="14" /> Shablon izohi</span>
      <span v-if="isAi && explanation.created_at" class="xs muted">{{ dateTime(explanation.created_at) }}</span>
      <span class="spacer" />
      <button v-if="canRegenerate" class="btn btn-sm" :disabled="busy" @click="$emit('regenerate')">
        <RefreshCw :size="13" :class="{ spin: busy }" /> {{ busy ? 'Yozilmoqda…' : 'Qayta yozish' }}
      </button>
    </div>

    <div v-if="warn" class="notice notice-warn small">
      <TriangleAlert :size="15" />
      <span>SI matni ko‘rsatilmadi: {{ explanation.fallback_reason }}. Quyida hisoblangan natijalardan tuzilgan shablon izohi.</span>
    </div>

    <p v-for="(p, i) in explanation.paragraphs" :key="i" class="ai-p">{{ p }}</p>

    <div class="ai-foot">
      <ShieldCheck :size="14" />
      <span v-if="isAi">
        {{ explanation.basis_note }} Model bahoni yaratmaydi: undagi har bir son hisoblangan natijalar bilan solishtirilgan.
      </span>
      <span v-else>{{ explanation.basis_note }} Izohda yangi raqam, manba yoki fakt yaratilmaydi.</span>
    </div>
  </div>
</template>

<style scoped>
.ai { display: flex; flex-direction: column; gap: 10px; }
.ai-head { display: flex; align-items: center; gap: 10px; }

.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--blue-50), var(--cyan-50));
  color: var(--blue-600);
  font-size: var(--fs-xs);
  font-weight: 650;
}

.ai-badge.tpl { background: var(--surface-3); color: var(--text-2); }
.ai-p { font-size: var(--fs-base); line-height: 1.65; color: var(--text); }
.ai-p:first-of-type { font-weight: 560; }

.ai-foot {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: var(--fs-xs);
}

.ai-foot svg { flex-shrink: 0; margin-top: 1px; color: var(--blue); }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
