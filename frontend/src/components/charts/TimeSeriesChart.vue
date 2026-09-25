<script setup lang="ts">
// 24 oylik vaqt qatori: subyekt qiymati, o'xshashlar medianasi, kutilgan oraliq va og'ishlar.
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { axisCommon, baseTooltip, FONT } from './echarts'
import type { TimeSeries } from '@/types/api'
import { monthYear, num, signed } from '@/utils/format'
import { HEX } from '@/utils/labels'

const props = defineProps<{ series: TimeSeries }>()

const option = computed(() => {
  const pts = props.series.points
  const labels = pts.map((p) => monthYear(p.period, true))
  const low = pts.map((p) => p.expected_low)
  const band = pts.map((p) => (p.expected_low !== null && p.expected_high !== null ? p.expected_high - p.expected_low : null))
  const digits = props.series.metric === 'tax_index' ? 3 : 1
  const hasRegistry = pts.some((p) => p.registry !== null)
  const outliers = pts
    .map((p, i) =>
      p.outside && p.value !== null && Math.abs(p.deviation_pct ?? 0) >= 25 ? { coord: [i, p.value], value: p.deviation_pct } : null,
    )
    .filter(Boolean)

  return {
    textStyle: { fontFamily: FONT },
    grid: { left: 8, right: 16, top: 34, bottom: 8, containLabel: true },
    legend: {
      top: 0,
      left: 0,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: { color: HEX.muted, fontSize: 11.5 },
      data: ['Subyekt qiymati', 'O‘xshashlar medianasi', 'Kutilgan oraliq', ...(hasRegistry ? ['Reyestr ma’lumoti'] : [])],
    },
    tooltip: {
      ...baseTooltip,
      trigger: 'axis',
      formatter: (params: { dataIndex: number }[]) => {
        const p = pts[params[0].dataIndex]
        const u = props.series.unit
        const rows = [
          `<b>${monthYear(p.period)}</b>`,
          `Qiymat: <b>${p.value === null ? 'ma’lumot mavjud emas' : `${num(p.value, digits)} ${u}`}</b>`,
          `Kutilgan: ${p.expected === null ? '—' : `${num(p.expected, digits)} ${u}`}`,
          p.expected_low !== null ? `Oraliq: ${num(p.expected_low, digits)} … ${num(p.expected_high, digits)}` : '',
          `O‘xshashlar medianasi: ${num(p.peer_median, digits)}`,
          p.deviation_pct !== null ? `Og‘ish: <b>${signed(p.deviation_pct, 1)}%</b>${p.outside ? ' · oraliqdan tashqari' : ''}` : '',
          p.registry !== null ? `Reyestr: ${num(p.registry, digits)}` : '',
        ]
        return rows.filter(Boolean).join('<br/>')
      },
    },
    xAxis: { type: 'category', data: labels, boundaryGap: false, ...axisCommon, splitLine: { show: false } },
    yAxis: { type: 'value', scale: true, ...axisCommon, axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => num(v, digits > 1 ? 2 : 0) } },
    series: [
      { name: 'band-base', type: 'line', stack: 'band', data: low, lineStyle: { opacity: 0 }, symbol: 'none', silent: true, tooltip: { show: false } },
      {
        name: 'Kutilgan oraliq',
        type: 'line',
        stack: 'band',
        data: band,
        lineStyle: { opacity: 0 },
        symbol: 'none',
        areaStyle: { color: 'rgba(56,189,248,0.16)' },
        itemStyle: { color: 'rgba(56,189,248,0.4)' },
        silent: true,
      },
      {
        name: 'O‘xshashlar medianasi',
        type: 'line',
        data: pts.map((p) => p.peer_median),
        symbol: 'none',
        lineStyle: { color: HEX.muted, width: 1.4, type: 'dashed' },
        itemStyle: { color: HEX.muted },
      },
      ...(hasRegistry
        ? [{
            name: 'Reyestr ma’lumoti',
            type: 'line',
            data: pts.map((p) => p.registry),
            symbol: 'none',
            lineStyle: { color: '#8B9BB4', width: 1.2, type: 'dotted' },
            itemStyle: { color: '#8B9BB4' },
          }]
        : []),
      {
        name: 'Subyekt qiymati',
        type: 'line',
        data: pts.map((p) => p.value),
        connectNulls: false,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { color: HEX.navy, width: 2.4 },
        itemStyle: { color: HEX.navy, borderColor: '#fff', borderWidth: 1 },
        markPoint: {
          symbol: 'circle',
          symbolSize: 13,
          itemStyle: { color: '#fff', borderColor: HEX.high, borderWidth: 2.5 },
          label: {
            show: true,
            position: 'bottom',
            distance: 6,
            color: HEX.high,
            fontSize: 10.5,
            fontWeight: 700,
            formatter: (p: { value: number }) => `${signed(p.value, 0)}%`,
          },
          data: outliers,
        },
      },
    ],
  }
})
</script>

<template>
  <VChart :option="option" autoresize style="height: 320px" />
</template>
