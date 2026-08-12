<template>
  <ChartBox>
    <Line :data="chartData" :options="options" />
  </ChartBox>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import ChartBox from './ChartBox.vue'
import { baseChartOptions, legendBoxWidth12, linearScale, timeScale } from './chartDefaults'

const props = defineProps({
  gas: { type: Array, required: true },
  maintenance: { type: Array, required: true },
})

const chartData = computed(() => ({
  datasets: [
    {
      label: 'Cumulative gas spend',
      data: props.gas,
      borderColor: '#ff8a3d',
      backgroundColor: 'rgba(255,138,61,0.12)',
      fill: true,
      pointRadius: 0,
      borderWidth: 2,
    },
    {
      label: 'Cumulative maintenance spend',
      data: props.maintenance,
      borderColor: '#f87171',
      backgroundColor: 'rgba(248,113,113,0.12)',
      fill: true,
      pointRadius: 0,
      borderWidth: 2,
    },
  ],
}))

const options = {
  ...baseChartOptions,
  plugins: { legend: legendBoxWidth12 },
  scales: {
    x: timeScale(),
    y: linearScale({ title: { display: true, text: 'Cumulative $' } }),
  },
}
</script>
