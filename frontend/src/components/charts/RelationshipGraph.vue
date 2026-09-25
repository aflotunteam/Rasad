<script setup lang="ts">
// Aloqadorliklar tarmog'i: sukut bo'yicha periferiya soddalashtirilgan ("spagetti" emas).
import { Crosshair, ExternalLink, Maximize2, Minimize2 } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import VChart from 'vue-echarts'
import { baseTooltip, FONT } from './echarts'
import RiskBadge from '@/components/risk/RiskBadge.vue'
import { useMetaStore } from '@/stores/meta'
import type { GraphNode, Relations } from '@/types/api'
import { num, score as fmtScore } from '@/utils/format'
import { HEX } from '@/utils/labels'

const props = defineProps<{ data: Relations; depth: number; height?: number }>()
const emit = defineEmits<{ 'update:depth': [number]; open: [string] }>()
const meta = useMetaStore()

const focusRisky = ref(false)
const structuralOnly = ref(false)
const selected = ref<GraphNode | null>(null)

const NODE_COLOR = { high: HEX.high, medium: HEX.medium, low: '#B7C3D3' }

const edges = computed(() => props.data.edges.filter((e) => !structuralOnly.value || e.structural))
const nodeIds = computed(() => {
  const ids = new Set<string>([props.data.center])
  edges.value.forEach((e) => {
    ids.add(e.source)
    ids.add(e.target)
  })
  return ids
})

const option = computed(() => {
  const riskyNodes = new Set<string>()
  if (focusRisky.value) {
    edges.value.filter((e) => e.risky_path).forEach((e) => {
      riskyNodes.add(e.source)
      riskyNodes.add(e.target)
    })
  }
  const nodes = props.data.nodes
    .filter((n) => nodeIds.value.has(n.id))
    .map((n) => {
      const dim = focusRisky.value && !riskyNodes.has(n.id) && !n.is_center
      const color = n.is_center ? HEX.navy : n.restricted || !n.level ? '#D5DDE8' : NODE_COLOR[n.level]
      return {
        id: n.id,
        name: n.id,
        value: n.score ?? 0,
        symbolSize: n.is_center ? 46 : n.depth === 1 ? 26 + (n.score ?? 0) / 8 : 18 + (n.score ?? 0) / 10,
        itemStyle: {
          color,
          borderColor: n.is_center ? '#38BDF8' : '#fff',
          borderWidth: n.is_center ? 4 : 2,
          opacity: dim ? 0.25 : 1,
          shadowBlur: n.is_center ? 16 : 0,
          shadowColor: 'rgba(33,109,243,0.35)',
        },
        label: {
          show: true,
          position: n.is_center ? 'inside' : 'bottom',
          color: n.is_center ? '#fff' : HEX.navy,
          fontSize: n.is_center ? 10 : 10.5,
          fontWeight: n.is_center ? 700 : 600,
          fontFamily: FONT,
          opacity: dim ? 0.3 : 1,
          formatter: () =>
            n.is_center
              ? n.id.replace('SUB-', '')
              : `${n.id}${n.score !== null ? `\n${fmtScore(n.score)}` : ''}${n.hidden_neighbors ? `  +${n.hidden_neighbors}` : ''}`,
        },
        raw: n,
      }
    })
  const links = edges.value.map((e) => {
    const dim = focusRisky.value && !e.risky_path
    return {
      source: e.source,
      target: e.target,
      value: e.weight,
      raw: e,
      lineStyle: {
        color: focusRisky.value && e.risky_path ? HEX.high : e.structural ? '#5E7699' : '#AEBBCC',
        width: e.structural ? 1.2 + e.weight * 2.2 : 1 + e.weight,
        type: e.structural ? 'solid' : 'dashed',
        opacity: dim ? 0.12 : 0.85,
        curveness: 0.06,
      },
    }
  })
  return {
    textStyle: { fontFamily: FONT },
    tooltip: {
      ...baseTooltip,
      formatter: (p: { dataType: string; data: { raw: Record<string, unknown> } }) => {
        const r = p.data.raw as Record<string, never>
        if (p.dataType === 'edge') {
          return `<b>${r.label}</b><br/>${r.source} ↔ ${r.target}<br/>Aloqa kuchi: ${num(r.weight, 2)}${r.risky_path ? '<br/>Xavfli yo‘l' : ''}`
        }
        const n = r as unknown as GraphNode
        if (n.restricted) return `<b>${n.id}</b><br/>Ruxsat mavjud emas`
        return `<b>${n.id}</b><br/>${meta.regionShort(n.region_id)} · ${meta.sectorName(n.sector_id)}<br/>Xavf bahosi: ${fmtScore(n.score)}${n.hidden_neighbors ? `<br/>Yashirilgan periferik aloqalar: ${n.hidden_neighbors}` : ''}`
      },
    },
    animationDuration: 400,
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data: nodes,
        links,
        force: { repulsion: 260, edgeLength: [70, 130], gravity: 0.08, friction: 0.35 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
        scaleLimit: { min: 0.4, max: 3 },
      },
    ],
  }
})

function onClick(p: { dataType?: string; data?: unknown }) {
  if (p.dataType !== 'node') return
  const raw = (p.data as { raw: GraphNode }).raw
  selected.value = raw.is_center ? null : raw
}
</script>

<template>
  <div class="rg">
    <div class="rg-tools">
      <div class="rg-seg" role="group" aria-label="Chuqurlik">
        <button :class="{ active: depth === 1 }" @click="emit('update:depth', 1)"><Minimize2 :size="13" /> To‘g‘ridan-to‘g‘ri</button>
        <button :class="{ active: depth === 2 }" @click="emit('update:depth', 2)"><Maximize2 :size="13" /> 2-daraja</button>
      </div>
      <label class="rg-check"><input v-model="structuralOnly" type="checkbox" /> Faqat tuzilmaviy aloqalar</label>
      <button class="btn btn-sm" :class="{ 'btn-dark': focusRisky }" :aria-pressed="focusRisky" @click="focusRisky = !focusRisky">
        <Crosshair :size="14" /> Xavfli yo‘lga fokus
      </button>
      <span class="spacer" />
      <span class="xs muted">G‘ildirak — masshtab, sichqoncha — surish</span>
    </div>

    <div class="rg-body">
      <VChart :option="option" autoresize :style="{ height: `${height ?? 400}px` }" @click="onClick" />
      <div v-if="selected" class="rg-card card">
        <div class="row">
          <span class="code">{{ selected.id }}</span>
          <span class="spacer" />
          <button class="btn btn-ghost btn-icon btn-sm" aria-label="Yopish" @click="selected = null">×</button>
        </div>
        <template v-if="!selected.restricted">
          <div class="xs muted">{{ meta.regionShort(selected.region_id) }} · {{ meta.sectorName(selected.sector_id) }}</div>
          <RiskBadge v-if="selected.level" :level="selected.level" :score="selected.score" size="sm" />
          <button class="btn btn-sm btn-primary" @click="emit('open', selected.id)"><ExternalLink :size="13" /> Kartani ochish</button>
        </template>
        <div v-else class="xs muted">Ruxsat mavjud emas: subyekt boshqa hududga tegishli.</div>
      </div>
    </div>

    <div class="rg-legend xs muted">
      <span><i class="dot" style="background: #0b1f3a" /> Tahlil qilinayotgan subyekt</span>
      <span><i class="dot" style="background: #d9534f" /> Yuqori xavf</span>
      <span><i class="dot" style="background: #d99b22" /> O‘rta xavf</span>
      <span><i class="dot" style="background: #b7c3d3" /> Past xavf</span>
      <span><i class="ln" /> Tuzilmaviy aloqa (muassis, rahbar, manzil)</span>
      <span><i class="ln dashed" /> Tijorat aloqasi</span>
      <span>+N — yashirilgan periferik aloqalar</span>
    </div>
  </div>
</template>

<style scoped>
.rg { display: flex; flex-direction: column; gap: 10px; }
.rg-tools { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.rg-seg { display: inline-flex; border: 1px solid var(--border-strong); border-radius: 9px; overflow: hidden; }

.rg-seg button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 11px;
  border: 0;
  background: #fff;
  color: var(--text-2);
  font-size: var(--fs-sm);
  cursor: pointer;
}

.rg-seg button + button { border-left: 1px solid var(--border-strong); }
.rg-seg button.active { background: var(--navy); color: #fff; }
.rg-check { display: inline-flex; align-items: center; gap: 6px; font-size: var(--fs-sm); color: var(--text-2); cursor: pointer; }
.rg-body { position: relative; border: 1px solid var(--border); border-radius: var(--radius); background: radial-gradient(circle at 50% 50%, #fbfdff, #f3f7fb); }

.rg-card {
  position: absolute;
  right: 12px;
  top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 220px;
  padding: 12px;
  box-shadow: var(--shadow-md);
}

.rg-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; }
.rg-legend span { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.ln { width: 20px; height: 0; border-top: 2px solid #5e7699; display: inline-block; }
.ln.dashed { border-top: 2px dashed #aebbcc; }
</style>
