<script setup lang="ts">
import { Info } from 'lucide-vue-next'
import { computed } from 'vue'
import RiskBadge from './RiskBadge.vue'
import RiskFactorList from './RiskFactorList.vue'
import UiDrawer from '@/components/ui/UiDrawer.vue'
import type { Factor, Risk } from '@/types/api'
import { num, score as fmtScore } from '@/utils/format'

const props = defineProps<{ open: boolean; code: string; risk: Risk; factors: Factor[] }>()
defineEmits<{ close: [] }>()

const total = computed(() => props.factors.reduce((s, f) => s + f.impact, 0))
const top3 = computed(() => props.factors.filter((f) => f.impact > 0).slice(0, 3))
</script>

<template>
  <UiDrawer :open="open" :title="`NEGA? — ${code}`" subtitle="Xavf bahosini shakllantirgan omillar" :width="620" @close="$emit('close')">
    <div class="why-summary">
      <div>
        <div class="section-label">Xavf bahosi</div>
        <div class="why-score num">{{ fmtScore(risk.score) }}<small>/100</small></div>
      </div>
      <RiskBadge :level="risk.level" />
      <div class="why-top">
        <div class="section-label">3 ta asosiy sabab</div>
        <ol>
          <li v-for="f in top3" :key="f.rank">{{ f.factor }} <b class="num">+{{ num(f.impact, 1) }}</b></li>
        </ol>
      </div>
    </div>

    <div class="notice notice-info">
      <Info :size="16" />
      <span>
        Har bir omilning ta’siri yakuniy bahoga proporsional taqsimlangan: ta’sirlar yig‘indisi
        <b class="num">{{ num(total, 1) }}</b> ball xavf bahosiga teng. Qiymatlar hisoblangan natijalardan olinadi.
      </span>
    </div>

    <h3 class="why-h">Barcha omillar</h3>
    <RiskFactorList :factors="factors" :score="risk.score" />

    <p class="xs muted why-foot">
      Model: {{ risk.model_version }} · Ma’lumot: {{ risk.data_version }}. Mazkur baho avtomatik tahlil natijasi bo‘lib,
      yakuniy huquqiy xulosa hisoblanmaydi.
    </p>
  </UiDrawer>
</template>

<style scoped>
.why-summary {
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: 18px;
  padding: 14px 16px;
  margin-bottom: 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface-2);
}

.why-score { font-size: 38px; font-weight: 760; color: var(--navy); letter-spacing: -0.03em; line-height: 1.05; }
.why-score small { font-size: 15px; color: var(--muted); font-weight: 560; }
.why-top ol { margin: 4px 0 0; padding-left: 18px; font-size: var(--fs-md); }
.why-top li { margin: 2px 0; }
.why-top b { color: var(--navy); margin-left: 4px; }
.why-h { margin: 18px 0 10px; }
.why-foot { margin-top: 14px; }
</style>
