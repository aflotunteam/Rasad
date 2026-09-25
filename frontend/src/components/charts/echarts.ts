// ECharts: faqat kerakli modullar ro'yxatdan o'tkaziladi (bundle hajmi uchun).
import { BarChart, CustomChart, GraphChart, LineChart, ScatterChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HEX } from '@/utils/labels'

use([
  BarChart,
  LineChart,
  GraphChart,
  ScatterChart,
  CustomChart,
  GridComponent,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  DataZoomComponent,
  CanvasRenderer,
])

export const FONT = "'Inter Variable', Inter, system-ui, sans-serif"

export const baseTooltip = {
  backgroundColor: '#0B1F3A',
  borderWidth: 0,
  padding: [8, 11],
  textStyle: { color: '#E8EEF7', fontFamily: FONT, fontSize: 12 },
  extraCssText: 'border-radius:8px; box-shadow:0 10px 24px -8px rgba(11,31,58,.45);',
}

export const axisCommon = {
  axisLine: { lineStyle: { color: HEX.border } },
  axisTick: { show: false },
  axisLabel: { color: HEX.muted, fontFamily: FONT, fontSize: 11 },
  splitLine: { lineStyle: { color: HEX.grid } },
}

export const textStyle = { fontFamily: FONT, color: HEX.navy }
