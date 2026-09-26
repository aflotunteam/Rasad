<script setup lang="ts">
import { ExternalLink, Scale } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { dataApi } from '@/services/api'
import type { Calibration } from '@/types/api'
import { date, num } from '@/utils/format'

const data = ref<Calibration | null>(null)
const error = ref(false)
const tab = ref<'sectors' | 'regions'>('sectors')

onMounted(async () => {
  try {
    data.value = await dataApi.calibration()
  } catch {
    error.value = true
  }
})

function asOf(v: string) {
  return v.length === 4 ? `${v}-yil` : date(v)
}
</script>

<template>
  <section class="card calib">
    <div class="card-head">
      <div>
        <div class="card-title"><Scale :size="18" class="ic" /> Sintetik ma’lumot kalibrlashi</div>
        <div class="card-sub">Tanlanma tuzilmasi rasmiy agregat statistikaga moslashtirilgan. Subyektlar va ularning ko‘rsatkichlari sun’iy.</div>
      </div>
    </div>
    <div class="card-body">
      <div v-if="error" class="notice notice-warn small">Kalibrlash ma’lumotini olib bo‘lmadi.</div>
      <LoadingSkeleton v-else-if="!data" :lines="6" />
      <div v-else class="calib-grid">
        <div class="col">
          <div class="section-label">Rasmiy manbalar</div>
          <ul class="sources">
            <li v-for="s in data.sources" :key="s.url + s.what">
              <div class="src-what">{{ s.what }}</div>
              <div class="xs muted">
                {{ s.publisher }} · holat: {{ asOf(s.as_of) }} ·
                <a :href="s.url" target="_blank" rel="noopener noreferrer">manba <ExternalLink :size="11" /></a>
              </div>
            </li>
          </ul>
          <div class="section-label">Taxminlar</div>
          <ul class="assump small">
            <li v-for="a in data.assumptions" :key="a">{{ a }}</li>
          </ul>
        </div>

        <div class="col">
          <div class="tabs" role="tablist">
            <button role="tab" :aria-selected="tab === 'sectors'" :class="{ active: tab === 'sectors' }" @click="tab = 'sectors'">Sohalar</button>
            <button role="tab" :aria-selected="tab === 'regions'" :class="{ active: tab === 'regions' }" @click="tab = 'regions'">Hududlar</button>
          </div>
          <table v-if="tab === 'sectors'" class="table">
            <thead>
              <tr>
                <th>Soha</th>
                <th class="right">Ulush: rasmiy / tanlanma</th>
                <th class="right">O‘rtacha oylik aylanma, mln so‘m: rasmiy / tanlanma</th>
                <th class="right">Mediana</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in data.check.sectors" :key="s.id">
                <td>{{ s.name }}</td>
                <td class="right num">{{ num(s.official_share, 1) }}% / {{ num(s.sample_share, 1) }}%</td>
                <td class="right num">{{ num(s.official_mean_monthly_mln, 1) }} / {{ num(s.sample_mean_monthly_mln, 1) }}</td>
                <td class="right num muted">{{ num(s.sample_median_monthly_mln, 1) }}</td>
              </tr>
            </tbody>
          </table>
          <table v-else class="table">
            <thead><tr><th>Hudud</th><th class="right">Rasmiy ulush</th><th class="right">Tanlanmada</th></tr></thead>
            <tbody>
              <tr v-for="r in data.check.regions" :key="r.id">
                <td>{{ r.name }}</td>
                <td class="right num">{{ num(r.official_share, 1) }}%</td>
                <td class="right num">{{ num(r.sample_share, 1) }}%</td>
              </tr>
            </tbody>
          </table>
          <p class="xs muted foot">
            O‘rtacha aylanma = 2025-yil rasmiy hajmi / faoliyat ko‘rsatayotgan korxonalar soni / 12. Mediana ancha past:
            hajmning katta qismi kam sonli yirik korxonalarga to‘g‘ri keladi. Kichik korxonalar ulushi tanlanmada
            {{ num(data.check.size_groups.small, 1) }}% (rasmiy 84,9%).
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.calib { margin-bottom: var(--gap); }
.card-title { display: inline-flex; align-items: center; gap: 8px; }
.ic { color: var(--blue); }
.calib-grid { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); gap: 24px; }
.col { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.sources { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 10px; }
.src-what { font-size: var(--fs-md); font-weight: 560; color: var(--navy); }
.sources a { display: inline-flex; align-items: center; gap: 2px; }
.assump { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 4px; color: var(--text-2); }
.tabs { display: inline-flex; border: 1px solid var(--border-strong); border-radius: 9px; overflow: hidden; align-self: flex-start; }
.tabs button { height: 30px; padding: 0 14px; border: 0; background: #fff; color: var(--text-2); font-size: var(--fs-sm); cursor: pointer; }
.tabs button + button { border-left: 1px solid var(--border-strong); }
.tabs button.active { background: var(--navy); color: #fff; }
.foot { margin-top: 4px; }
</style>
