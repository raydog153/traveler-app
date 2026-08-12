<template>
  <ChartBox>
    <Bar :data="chartData" :options="options" />
  </ChartBox>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import ChartBox from './ChartBox.vue'
import { baseChartOptions, legendBoxWidth12, linearScale } from './chartDefaults'

const props = defineProps({
  yearly: { type: Array, required: true },
})

const chartData = computed(() => ({
  // The most recent year is still accumulating, so mark it as partial --
  // matches the original dashboard's "2026 is partial" note, generalized to
  // whichever year is last rather than a hardcoded year.
  labels: props.yearly.map((y, i) => (i === props.yearly.length - 1 ? `${y.year}*` : y.year)),
  datasets: [
    {
      type: 'bar',
      label: 'Gas spend ($)',
      data: props.yearly.map((y) => y.cost),
      backgroundColor: '#ff8a3d',
      yAxisID: 'y',
      borderRadius: 6,
    },
    {
      type: 'line',
      label: 'Miles driven',
      data: props.yearly.map((y) => y.miles),
      borderColor: '#3ddcff',
      yAxisID: 'y1',
      borderWidth: 2.5,
      tension: 0.2,
    },
  ],
}))

const options = {
  ...baseChartOptions,
  plugins: { legend: legendBoxWidth12 },
  scales: {
    y: linearScale({ position: 'left', title: { display: true, text: '$ spent' } }),
    y1: { position: 'right', grid: { display: false }, title: { display: true, text: 'miles' } },
  },
}
</script>
