<script setup lang="ts">
import { ShieldCheck, Sparkles } from 'lucide-vue-next'
import type { Explanation } from '@/types/api'

defineProps<{ explanation: Explanation }>()
</script>

<template>
  <div class="ai">
    <div class="ai-badge"><Sparkles :size="14" /> Sun’iy intellekt izohi</div>
    <p v-for="(p, i) in explanation.paragraphs" :key="i" class="ai-p">{{ p }}</p>
    <div class="ai-foot">
      <ShieldCheck :size="14" />
      <span>{{ explanation.basis_note }} Izohda yangi raqam, manba yoki fakt yaratilmaydi.</span>
    </div>
  </div>
</template>

<style scoped>
.ai { display: flex; flex-direction: column; gap: 10px; }

.ai-badge {
  align-self: flex-start;
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
</style>
