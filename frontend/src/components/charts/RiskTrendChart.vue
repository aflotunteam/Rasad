<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { axisCommon, baseTooltip, FONT } from './echarts'
import type { Dashboard } from '@/types/api'
import { monthYear, num } from '@/utils/format'
import { HEX } from '@/utils/labels'

const props = defineProps<{ trend: Dashboard['trend'] }>()

const option = computed(() => ({
  textStyle: { fontFamily: FONT },
  grid: { left: 6, right: 22, top: 22, bottom: 4, containLabel: true },
  tooltip: {
    ...baseTooltip,
    trigger: 'axis',
    formatter: (p: { dataIndex: number }[]) => {
      const r = props.trend[p[0].dataIndex]
      return `<b>${monthYear(r.period)}</b><br/>Yuqori ustuvorlik ulushi: ${num(r.high_share * 100, 2)}%<br/>O‘rtacha xavf bahosi: ${num(r.mean_score, 1)}`
    },
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: props.trend.map((t) => monthYear(t.period, true)),
    ...axisCommon,
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    ...axisCommon,
    axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `${num(v, 1)}%` },
    splitNumber: 3,
  },
  series: [
    {
      type: 'line',
      smooth: 0.25,
      symbol: 'circle',
      symbolSize: 6,
      data: props.trend.map((t) => +(t.high_share * 100).toFixed(2)),
      lineStyle: { color: HEX.blue, width: 2.2 },
      itemStyle: { color: HEX.blue, borderColor: '#fff', borderWidth: 1.5 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(33,109,243,0.16)' },
            { offset: 1, color: 'rgba(33,109,243,0)' },
          ],
        },
      },
      label: {
        show: true,
        position: 'top',
        fontSize: 10.5,
        color: HEX.muted,
        formatter: (p: { value: number }) => `${num(p.value, 1)}%`,
      },
    },
  ],
}))
</script>

<template>
  <VChart :option="option" autoresize style="height: 220px" />
</template>
