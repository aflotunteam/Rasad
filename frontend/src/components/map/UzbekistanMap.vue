<script setup lang="ts">
// O'zbekiston xaritasi: geoBoundaries ADM1 (14 ma'muriy birlik) + MapLibre GL.
// Rang shkalasi analitik ko'rsatkichni bildiradi, rasmiy statistikani emas.
import maplibregl, { type GeoJSONSource, type MapLayerMouseEvent } from 'maplibre-gl'
import { Minus, Plus, RotateCcw } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { RegionStat } from '@/types/api'
import { num, relative } from '@/utils/format'

const props = defineProps<{ regions: RegionStat[]; selected: string | null; height?: number }>()
const emit = defineEmits<{ select: [string | null] }>()

const el = ref<HTMLDivElement | null>(null)
const failed = ref(false)
let map: maplibregl.Map | null = null
let popup: maplibregl.Popup | null = null
let geo: GeoJSON.FeatureCollection | null = null
const labelMarkers: maplibregl.Marker[] = []
const BOUNDS: [[number, number], [number, number]] = [[55.9, 37.1], [73.2, 45.6]]

// Bir rangli ketma-ket shkala (och ko'k → to'q navy): xavf ranglaridan alohida.
// Chegaralar hududlar qiymatlaridan teng oraliqlarga bo'linadi (5 sinf).
const COLORS = ['#DCE9F9', '#A9C9F2', '#6FA3EA', '#2F74E6', '#1A4FB0']

const breaks = computed(() => {
  const vals = props.regions.filter((r) => !r.restricted && r.risk_index !== null).map((r) => r.risk_index as number)
  if (!vals.length) return [0, 1, 2, 3, 4]
  const lo = Math.floor(Math.min(...vals) * 2) / 2
  const hi = Math.ceil(Math.max(...vals) * 2) / 2
  const step = Math.max(0.5, (hi - lo) / 5)
  return COLORS.map((_, i) => +(lo + step * i).toFixed(1))
})

const legend = computed(() =>
  COLORS.map((c, i) => {
    const from = breaks.value[i]
    const to = breaks.value[i + 1]
    return { color: c, label: to === undefined ? `≥ ${num(from, 1)}%` : `${num(from, 1)}–${num(to, 1)}%` }
  }),
)

function colorExpr(): never {
  const b = breaks.value
  return ['step', ['get', 'risk'], COLORS[0], ...b.slice(1).flatMap((v, i) => [v, COLORS[i + 1]])] as never
}

const NEIGHBORS: [string, [number, number]][] = [
  ['QOZOG‘ISTON', [66.4, 44.9]],
  ['TURKMANISTON', [59.8, 39.2]],
  ['TOJIKISTON', [70.2, 38.4]],
  ['QIRG‘IZISTON', [73.6, 41.7]],
  ['AFG‘ONISTON', [66.9, 36.95]],
]

function stat(id: string) {
  return props.regions.find((r) => r.id === id)
}

function enrich(): GeoJSON.FeatureCollection | null {
  if (!geo) return null
  return {
    type: 'FeatureCollection',
    features: geo.features.map((f) => {
      const s = stat(String(f.properties?.region_id))
      return {
        ...f,
        properties: {
          ...f.properties,
          risk: s?.risk_index ?? -1,
          restricted: s?.restricted ? 1 : 0,
          selected: s?.id === props.selected ? 1 : 0,
        },
      }
    }),
  }
}

function centroid(f: GeoJSON.Feature): [number, number] {
  // Eng katta poligonning og'irlik markazi (yorliq joyi uchun yetarli aniqlik).
  const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates
  let best = polys[0]
  let bestArea = 0
  for (const p of polys) {
    const ring = p[0]
    let a = 0
    for (let i = 0; i < ring.length - 1; i++) a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    if (Math.abs(a) > bestArea) {
      bestArea = Math.abs(a)
      best = p
    }
  }
  const ring = best[0]
  let cx = 0
  let cy = 0
  let a = 0
  for (let i = 0; i < ring.length - 1; i++) {
    const cross = ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    a += cross
    cx += (ring[i][0] + ring[i + 1][0]) * cross
    cy += (ring[i][1] + ring[i + 1][1]) * cross
  }
  return [cx / (3 * a), cy / (3 * a)]
}

// Kichik va zich hududlar uchun yorliq joyi qo'lda belgilanadi (bir-birini bosmasligi uchun).
const LABEL_POS: Record<string, [number, number]> = {
  TK: [69.25, 41.31],
  TO: [70.35, 41.95],
  NG: [71.2, 41.0],
  AN: [72.4, 40.75],
  FA: [71.6, 40.4],
  SI: [68.72, 40.42],
  JI: [67.55, 40.22],
}

function renderLabels() {
  labelMarkers.forEach((m) => m.remove())
  labelMarkers.length = 0
  if (!map || !geo) return
  for (const f of geo.features) {
    const id = String(f.properties?.region_id)
    const s = stat(id)
    const [x, y] = LABEL_POS[id] ?? centroid(f)
    const node = document.createElement('div')
    node.className = 'map-label' + (s?.id === props.selected ? ' is-selected' : '') + (s?.restricted ? ' is-restricted' : '')
    const name = document.createElement('span')
    name.className = 'map-label-name'
    name.textContent = s?.short_name ?? id
    node.appendChild(name)
    if (s && !s.restricted && s.risk_index !== null) {
      const v = document.createElement('span')
      v.className = 'map-label-value'
      v.textContent = `${num(s.risk_index, 1)}%`
      node.appendChild(v)
    }
    labelMarkers.push(new maplibregl.Marker({ element: node }).setLngLat([x, y]).addTo(map))
  }
  for (const [label, pos] of NEIGHBORS) {
    const n = document.createElement('div')
    n.className = 'map-neighbor'
    n.textContent = label
    labelMarkers.push(new maplibregl.Marker({ element: n }).setLngLat(pos).addTo(map))
  }
}

function tooltipHtml(s: RegionStat): string {
  if (s.restricted) {
    return `<div class="mt-title">${s.name}</div><div class="mt-note">Ruxsat mavjud emas: hudud sizga biriktirilmagan.</div>`
  }
  const row = (k: string, v: string) => `<div class="mt-row"><span>${k}</span><b>${v}</b></div>`
  return (
    `<div class="mt-title">${s.name}</div>` +
    row('Subyektlar soni', num(s.subjects)) +
    row('Analitik xavf ko‘rsatkichi', `${num(s.risk_index, 1)}%`) +
    row('Yuqori ustuvorlikdagi holatlar', num(s.high)) +
    row('Yangi ogohlantirishlar', num(s.new_alerts)) +
    row('Ma’lumot yangilangan', relative(s.updated_at)) +
    `<div class="mt-note">Analitik ko‘rsatkich — o‘rta va yuqori darajali holatlar ulushi. Rasmiy statistika emas.</div>`
  )
}

function update() {
  const src = map?.getSource('regions') as GeoJSONSource | undefined
  const data = enrich()
  if (src && data) src.setData(data)
  if (map?.getLayer('fill')) {
    map.setPaintProperty('fill', 'fill-color', [
      'case',
      ['==', ['get', 'restricted'], 1],
      '#E9EEF4',
      ['<', ['get', 'risk'], 0],
      '#E9EEF4',
      colorExpr(),
    ] as never)
  }
  renderLabels()
}

async function init() {
  if (!el.value) return
  try {
    const res = await fetch('/geo/uzb_adm1.json')
    geo = await res.json()
  } catch {
    failed.value = true
    return
  }
  map = new maplibregl.Map({
    container: el.value,
    style: {
      version: 8,
      sources: {},
      layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#F3F7FB' } }],
    },
    bounds: BOUNDS,
    fitBoundsOptions: { padding: 24 },
    attributionControl: false,
    dragRotate: false,
    pitchWithRotate: false,
    touchPitch: false,
    renderWorldCopies: false,
    maxBounds: [[50, 33], [79, 49]],
    minZoom: 3.5,
    maxZoom: 9,
  })
  map.touchZoomRotate.disableRotation()
  map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: '© geoBoundaries / OpenStreetMap (ODbL)' }))

  map.on('load', () => {
    if (!map) return
    map.addSource('regions', { type: 'geojson', data: enrich()!, promoteId: 'region_id' })
    map.addLayer({
      id: 'fill',
      type: 'fill',
      source: 'regions',
      paint: {
        'fill-color': [
          'case',
          ['==', ['get', 'restricted'], 1],
          '#E9EEF4',
          ['<', ['get', 'risk'], 0],
          '#E9EEF4',
          colorExpr(),
        ],
        'fill-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.86, 1],
      },
    })
    map.addLayer({
      id: 'line',
      type: 'line',
      source: 'regions',
      paint: { 'line-color': '#FFFFFF', 'line-width': 1.2 },
    })
    map.addLayer({
      id: 'selected',
      type: 'line',
      source: 'regions',
      filter: ['==', ['get', 'selected'], 1],
      paint: { 'line-color': '#0B1F3A', 'line-width': 2.6 },
    })
    renderLabels()
  })

  let hovered: string | null = null
  popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 14, className: 'map-tip', maxWidth: '280px' })
  map.on('mousemove', 'fill', (e: MapLayerMouseEvent) => {
    if (!map || !e.features?.length) return
    const id = String(e.features[0].properties?.region_id)
    if (hovered !== id) {
      if (hovered) map.setFeatureState({ source: 'regions', id: hovered }, { hover: false })
      hovered = id
      map.setFeatureState({ source: 'regions', id }, { hover: true })
    }
    map.getCanvas().style.cursor = 'pointer'
    const s = stat(id)
    if (s) popup!.setLngLat(e.lngLat).setHTML(tooltipHtml(s)).addTo(map)
  })
  map.on('mouseleave', 'fill', () => {
    if (!map) return
    if (hovered) map.setFeatureState({ source: 'regions', id: hovered }, { hover: false })
    hovered = null
    map.getCanvas().style.cursor = ''
    popup?.remove()
  })
  map.on('click', 'fill', (e: MapLayerMouseEvent) => {
    const id = String(e.features?.[0]?.properties?.region_id)
    const s = stat(id)
    if (!s || s.restricted) return
    emit('select', props.selected === id ? null : id)
  })
}

function zoom(delta: number) {
  map?.easeTo({ zoom: (map.getZoom() ?? 5) + delta, duration: 200 })
}

function reset() {
  map?.fitBounds(BOUNDS, { padding: 24, duration: 250 })
}

watch(() => [props.regions, props.selected], update, { deep: true })
onMounted(init)
onBeforeUnmount(() => {
  popup?.remove()
  map?.remove()
  map = null
})
</script>

<template>
  <div class="uzmap" :style="{ height: `${height ?? 430}px` }">
    <div ref="el" class="uzmap-canvas" role="application" aria-label="O‘zbekiston hududlari xaritasi. Hududni tanlash uchun ro‘yxatdan ham foydalanish mumkin." />
    <div v-if="failed" class="uzmap-fail">Xarita qatlamini yuklab bo‘lmadi</div>
    <div class="uzmap-ctrl">
      <button class="btn btn-sm btn-icon" aria-label="Yaqinlashtirish" @click="zoom(0.6)"><Plus :size="15" /></button>
      <button class="btn btn-sm btn-icon" aria-label="Uzoqlashtirish" @click="zoom(-0.6)"><Minus :size="15" /></button>
      <button class="btn btn-sm btn-icon" aria-label="Boshlang‘ich ko‘rinish" @click="reset"><RotateCcw :size="14" /></button>
    </div>
    <div class="uzmap-legend">
      <div class="lg-title">Analitik xavf ko‘rsatkichi</div>
      <div class="lg-scale">
        <div v-for="l in legend" :key="l.label" class="lg-step">
          <i :style="{ background: l.color }" />
          <span>{{ l.label }}</span>
        </div>
      </div>
      <div class="lg-note">O‘rta va yuqori holatlar ulushi. Rasmiy statistika emas.</div>
    </div>
  </div>
</template>

<style scoped>
.uzmap { position: relative; border-radius: var(--radius); overflow: hidden; background: #f3f7fb; }
.uzmap-canvas { position: absolute; inset: 0; }
.uzmap-fail { position: absolute; inset: 0; display: grid; place-items: center; color: var(--muted); }

.uzmap-ctrl {
  position: absolute;
  right: 12px;
  top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.uzmap-ctrl .btn { background: rgba(255, 255, 255, 0.95); box-shadow: var(--shadow-xs); }

.uzmap-legend {
  position: absolute;
  left: 12px;
  bottom: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xs);
  max-width: 210px;
}

.lg-title { font-size: var(--fs-xs); font-weight: 650; color: var(--navy); margin-bottom: 6px; }
.lg-scale { display: flex; flex-direction: column; gap: 3px; }
.lg-step { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-2); white-space: nowrap; }
.lg-step i { width: 14px; height: 10px; border-radius: 2px; border: 1px solid rgba(11, 31, 58, 0.08); }
.lg-note { margin-top: 6px; font-size: 10.5px; color: var(--muted); line-height: 1.35; }
</style>

<style>
.map-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  pointer-events: none;
  text-align: center;
  line-height: 1.1;
}

.map-label-name {
  font-size: 11px;
  font-weight: 650;
  color: #0b1f3a;
  text-shadow: 0 0 3px #fff, 0 0 3px #fff, 0 0 2px #fff;
  white-space: nowrap;
}

.map-label-value {
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.92);
  color: #0b1f3a;
  font-size: 10.5px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
  box-shadow: 0 1px 2px rgba(11, 31, 58, 0.15);
}

.map-label.is-selected .map-label-value { background: #0b1f3a; color: #fff; }
.map-label.is-restricted .map-label-name { color: #8795a8; }

.map-neighbor {
  pointer-events: none;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: #9aa9bb;
}

.map-tip .maplibregl-popup-content {
  padding: 10px 12px;
  background: #0b1f3a;
  color: #e8eef7;
  border-radius: 9px;
  box-shadow: 0 12px 28px -10px rgba(11, 31, 58, 0.5);
  font-family: 'Inter Variable', Inter, system-ui, sans-serif;
}

.map-tip .maplibregl-popup-tip { display: none; }
.map-tip .mt-title { font-size: 13px; font-weight: 650; color: #fff; margin-bottom: 6px; }
.map-tip .mt-row { display: flex; justify-content: space-between; gap: 16px; font-size: 12px; color: #9fb0c8; padding: 1px 0; }
.map-tip .mt-row b { color: #fff; font-weight: 600; font-variant-numeric: tabular-nums; }
.map-tip .mt-note { margin-top: 6px; font-size: 10.5px; color: #7f93b0; line-height: 1.35; }
</style>
