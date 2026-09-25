<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { axisCommon, baseTooltip, FONT } from './echarts'
import type { Dashboard } from '@/types/api'
import { num } from '@/utils/format'
import { HEX } from '@/utils/labels'

const props = defineProps<{ sectors: Dashboard['sectors'] }>()

const option = computed(() => {
  const rows = [...props.sectors].sort((a, b) => a.share - b.share)
  return {
    textStyle: { fontFamily: FONT },
    grid: { left: 8, right: 44, top: 6, bottom: 4, containLabel: true },
    tooltip: {
      ...baseTooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(33,109,243,0.06)' } },
      formatter: (p: { dataIndex: number }[]) => {
        const r = rows[p[0].dataIndex]
        return `<b>${r.name}</b><br/>Subyektlar: ${num(r.subjects)}<br/>Yuqori: ${num(r.high)} · O‘rta: ${num(r.medium)}<br/>Ulush: ${num(r.share, 1)}%`
      },
    },
    xAxis: { type: 'value', ...axisCommon, axisLabel: { ...axisCommon.axisLabel, formatter: '{value}%' }, splitNumber: 3 },
    yAxis: { type: 'category', data: rows.map((r) => r.name), ...axisCommon, axisLine: { show: false } },
    series: [
      {
        name: 'Yuqori',
        type: 'bar',
        stack: 's',
        barWidth: 11,
        data: rows.map((r) => +((r.high / Math.max(1, r.subjects)) * 100).toFixed(2)),
        itemStyle: { color: HEX.high, borderRadius: [2, 0, 0, 2] },
      },
      {
        name: 'O‘rta',
        type: 'bar',
        stack: 's',
        data: rows.map((r) => +((r.medium / Math.max(1, r.subjects)) * 100).toFixed(2)),
        itemStyle: { color: HEX.medium, borderRadius: [0, 2, 2, 0] },
        label: {
          show: true,
          position: 'right',
          color: HEX.navy,
          fontSize: 11,
          fontWeight: 600,
          formatter: (p: { dataIndex: number }) => `${num(rows[p.dataIndex].share, 1)}%`,
        },
      },
    ],
  }
})
</script>

<template>
  <VChart :option="option" autoresize style="height: 290px" />
</template>
