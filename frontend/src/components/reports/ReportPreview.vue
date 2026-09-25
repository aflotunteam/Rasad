<script setup lang="ts">
import { FileSpreadsheet, FileText, FileType2 } from 'lucide-vue-next'
import { ref } from 'vue'
import BrandMark from '@/components/layout/BrandMark.vue'
import ConfidenceBadge from '@/components/risk/ConfidenceBadge.vue'
import RiskBadge from '@/components/risk/RiskBadge.vue'
import RiskFactorList from '@/components/risk/RiskFactorList.vue'
import { reportsApi } from '@/services/api'
import { ApiError } from '@/services/http'
import { useUiStore } from '@/stores/ui'
import type { ReportResult } from '@/types/api'
import { dateTime, num, periodRange, score as fmtScore } from '@/utils/format'
import { DECISION_LABEL, EXPERT_STATUS_LABEL } from '@/utils/labels'

const props = defineProps<{ report: ReportResult }>()
const ui = useUiStore()
const busy = ref<string | null>(null)

async function download(fmt: 'pdf' | 'xlsx' | 'csv') {
  busy.value = fmt
  try {
    await reportsApi.download(props.report.id, fmt)
    ui.toast(`Hisobot ${fmt.toUpperCase()} formatida yuklab olindi`, 'success')
  } catch (e) {
    ui.toast(e instanceof ApiError ? e.message : 'Yuklab bo‘lmadi', 'error')
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <div class="rp">
    <div class="rp-actions">
      <span class="section-label">Eksport</span>
      <button class="btn btn-sm btn-primary" :disabled="!!busy" @click="download('pdf')"><FileText :size="14" /> PDF</button>
      <button class="btn btn-sm" :disabled="!!busy" @click="download('xlsx')"><FileSpreadsheet :size="14" /> XLSX</button>
      <button class="btn btn-sm" :disabled="!!busy" @click="download('csv')"><FileType2 :size="14" /> CSV</button>
      <span v-if="busy" class="xs muted">Hisobot yaratilmoqda…</span>
    </div>

    <article class="paper">
      <header class="paper-head">
        <div class="row">
          <BrandMark :size="30" :dark="false" />
          <div>
            <div class="paper-brand">RASAD</div>
            <div class="xs muted">{{ report.meta.type_label }}</div>
          </div>
          <span class="spacer" />
          <span class="paper-synth">NAMOYISH MA’LUMOTLARI — SINTETIK</span>
        </div>
        <h2 class="paper-title">{{ report.meta.title }}</h2>
        <dl class="paper-meta">
          <div><dt>Hisobot raqami</dt><dd class="num">{{ report.meta.number }}</dd></div>
          <div><dt>Yaratilgan vaqt</dt><dd class="num">{{ dateTime(report.meta.created_at) }}</dd></div>
          <div><dt>Ma’lumot davri</dt><dd>{{ periodRange(report.meta.period_start, report.meta.period_end) }}</dd></div>
          <div><dt>Model versiyasi</dt><dd>{{ report.meta.model_version }}</dd></div>
          <div><dt>Ma’lumot versiyasi</dt><dd>{{ report.meta.data_version }}</dd></div>
          <div><dt>Yaratgan foydalanuvchi</dt><dd>{{ report.meta.created_by }}</dd></div>
        </dl>
      </header>

      <template v-if="report.content.kind === 'subject'">
        <section class="paper-sec">
          <h3>Umumiy ma’lumot</h3>
          <div class="kv">
            <div><span>Ichki kod</span><b class="code">{{ report.content.subject.code }}</b></div>
            <div><span>Hudud</span><b>{{ report.content.subject.region.name }}</b></div>
            <div><span>Faoliyat turi</span><b>{{ report.content.subject.sector.name }}</b></div>
            <div><span>STIR</span><b class="num">{{ report.content.subject.stir }}</b></div>
            <div><span>Xavf bahosi</span><RiskBadge :level="report.content.risk.level" :score="report.content.risk.score" size="sm" /></div>
            <div><span>Ishonch darajasi</span><ConfidenceBadge :level="report.content.risk.confidence" size="sm" /></div>
            <div><span>Ma’lumot sifati</span><b class="num">{{ num(report.content.risk.dq_score, 1) }} / 100</b></div>
            <div><span>Ekspert holati</span><b>{{ EXPERT_STATUS_LABEL[report.content.risk.expert_status] }}</b></div>
          </div>
        </section>
        <section class="paper-sec">
          <h3>Xavf sabablari</h3>
          <RiskFactorList :factors="report.content.factors" :score="report.content.risk.score" :limit="5" />
        </section>
        <section class="paper-sec">
          <h3>Sun’iy intellekt izohi</h3>
          <p v-for="(p, i) in report.content.explanation.paragraphs" :key="i" class="paper-p">{{ p }}</p>
          <p class="xs muted">{{ report.content.explanation.basis_note }}</p>
        </section>
        <section class="paper-sec">
          <h3>Aloqadorliklar</h3>
          <p class="paper-p">
            To‘g‘ridan-to‘g‘ri aloqalar: {{ report.content.relations.direct }} ta, shundan xavf darajasi o‘rta yoki yuqori:
            {{ report.content.relations.risky_direct }} ta.
          </p>
        </section>
        <section class="paper-sec">
          <h3>Ekspert qarorlari</h3>
          <p v-if="!report.content.decisions.length" class="paper-p muted">Ekspert qarori hali qabul qilinmagan.</p>
          <ul v-else class="dec">
            <li v-for="d in report.content.decisions" :key="d.id">
              <b>{{ DECISION_LABEL[d.decision] }}</b> · {{ dateTime(d.created_at) }} · {{ d.user.full_name }}
              <div class="muted">{{ d.comment }}</div>
            </li>
          </ul>
        </section>
      </template>

      <template v-else>
        <section class="paper-sec">
          <h3>Umumiy ko‘rsatkichlar</h3>
          <div class="kv kv-4">
            <div><span>Tahlil qilingan subyektlar</span><b class="num">{{ num(report.content.summary.subjects) }}</b></div>
            <div><span>Yuqori ustuvorlik</span><b class="num">{{ num(report.content.summary.high) }}</b></div>
            <div><span>O‘rta ustuvorlik</span><b class="num">{{ num(report.content.summary.medium) }}</b></div>
            <div><span>O‘rtacha ma’lumot sifati</span><b class="num">{{ num(report.content.summary.avg_dq, 1) }}</b></div>
          </div>
          <p class="xs muted">
            Xavf chegaralari: {{ report.content.summary.thresholds.low }} / {{ report.content.summary.thresholds.high }} (MVP uchun sozlanadigan qiymatlar).
          </p>
        </section>
        <section v-if="report.content.by_risk_type.length" class="paper-sec">
          <h3>Xavf turlari bo‘yicha</h3>
          <div class="chips">
            <span v-for="t in report.content.by_risk_type" :key="t.code" class="chip">{{ t.code }} {{ t.name }} · <b class="num">{{ t.count }}</b></span>
          </div>
        </section>
        <section class="paper-sec">
          <h3>Eng yuqori ustuvorlikdagi holatlar</h3>
          <table class="table">
            <thead>
              <tr><th>Ichki kod</th><th>Hudud</th><th>Soha</th><th class="right">Baho</th><th>Daraja</th><th>Ishonch</th><th>Tur</th><th class="right">Sifat</th></tr>
            </thead>
            <tbody>
              <tr v-for="t in report.content.top" :key="t.code">
                <td class="code">{{ t.code }}</td>
                <td>{{ t.region }}</td>
                <td>{{ t.sector }}</td>
                <td class="right num">{{ fmtScore(t.score) }}</td>
                <td>{{ t.level }}</td>
                <td>{{ t.confidence }}</td>
                <td>{{ t.risk_type }}</td>
                <td class="right num">{{ num(t.dq_score, 0) }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </template>

      <footer class="paper-foot">{{ report.meta.disclaimer }}</footer>
    </article>
  </div>
</template>

<style scoped>
.rp { display: flex; flex-direction: column; gap: 12px; }
.rp-actions { display: flex; align-items: center; gap: 8px; }
.paper { background: #fff; border: 1px solid var(--border); border-radius: 6px; box-shadow: var(--shadow-md); padding: 34px 40px; max-width: 860px; }
.paper-head { padding-bottom: 18px; border-bottom: 2px solid var(--navy); }
.paper-brand { font-weight: 760; letter-spacing: 0.14em; color: var(--navy); }
.paper-synth { font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em; color: var(--blue-600); border: 1px dashed #9cc0f5; padding: 3px 8px; border-radius: 4px; }
.paper-title { margin: 16px 0 12px; font-size: 21px; }
.paper-meta { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px 16px; margin: 0; }
.paper-meta dt { font-size: 10.5px; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); }
.paper-meta dd { margin: 1px 0 0; font-size: var(--fs-md); font-weight: 560; }
.paper-sec { padding: 16px 0 4px; }
.paper-sec h3 { font-size: var(--fs-lg); margin-bottom: 10px; }
.paper-p { line-height: 1.6; margin-bottom: 8px; }
.kv { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px 24px; }
.kv-4 { grid-template-columns: repeat(4, 1fr); }
.kv div { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: var(--fs-md); }
.kv-4 div { flex-direction: column; align-items: flex-start; border: 0; }
.kv span { color: var(--muted); }
.kv-4 b { font-size: 22px; color: var(--navy); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.dec { margin: 0; padding-left: 18px; }
.dec li { margin-bottom: 8px; }
.paper-foot { margin-top: 20px; padding-top: 12px; border-top: 1px solid var(--border); font-size: var(--fs-xs); color: var(--muted); }
</style>
