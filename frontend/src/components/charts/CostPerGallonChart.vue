<template>
  <ChartBox>
    <Line :data="chartData" :options="options" />
  </ChartBox>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import ChartBox from './ChartBox.vue'
import { baseChartOptions, linearScale, timeScale } from './chartDefaults'

const props = defineProps({
  series: { type: Array, required: true },
})

const chartData = computed(() => ({
  datasets: [
    {
      label: 'Cost / gallon ($)',
      data: props.series,
      borderColor: '#ff8a3d',
      backgroundColor: 'rgba(255,138,61,0.08)',
      pointRadius: 0,
      borderWidth: 2,
      fill: true,
      tension: 0.15,
    },
  ],
}))

const options = {
  ...baseChartOptions,
  plugins: { legend: { display: false } },
  scales: {
    x: timeScale(),
    y: linearScale({ title: { display: true, text: '$/gal' } }),
  },
}
</script>
