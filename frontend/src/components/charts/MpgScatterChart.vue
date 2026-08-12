<template>
  <ChartBox>
    <Scatter :data="chartData" :options="options" />
  </ChartBox>
</template>

<script setup>
import { computed } from 'vue'
import { Scatter } from 'vue-chartjs'
import ChartBox from './ChartBox.vue'
import { baseChartOptions, legendBoxWidth12, linearScale, timeScale } from './chartDefaults'

const props = defineProps({
  cleanPoints: { type: Array, required: true },
  excludedPoints: { type: Array, required: true },
  rollingAvg: { type: Array, required: true },
  majorEvents: { type: Array, required: true },
})

const chartData = computed(() => ({
  datasets: [
    {
      label: 'Excluded (partial/est.)',
      data: props.excludedPoints,
      backgroundColor: 'rgba(143,161,179,0.35)',
      pointRadius: 3,
    },
    {
      label: 'Fill-up MPG',
      data: props.cleanPoints,
      backgroundColor: 'rgba(61,220,255,0.3)',
      pointRadius: 2.5,
    },
    {
      type: 'line',
      label: '7-fillup rolling avg',
      data: props.rollingAvg,
      borderColor: '#3ddcff',
      borderWidth: 2.5,
      pointRadius: 0,
      tension: 0.25,
    },
  ],
}))

const options = computed(() => {
  const annotations = {}
  props.majorEvents.forEach((e, i) => {
    annotations[`maint${i}`] = {
      type: 'line',
      xMin: e.date,
      xMax: e.date,
      borderColor: e.cost > 10000 ? '#f87171' : 'rgba(167,139,250,0.55)',
      borderWidth: e.cost > 10000 ? 2 : 1,
      borderDash: e.cost > 10000 ? [] : [4, 3],
    }
  })
  return {
    ...baseChartOptions,
    plugins: {
      legend: legendBoxWidth12,
      annotation: { annotations },
    },
    scales: {
      x: timeScale(),
      // Hard cap (not just a suggested max): a bad odometer entry in the
      // source data can otherwise blow up the axis to fit one outlier point
      // and squash every real value into unreadable near-zero territory.
      y: linearScale({ title: { display: true, text: 'MPG' }, min: 0, max: 25 }),
    },
  }
})
</script>
