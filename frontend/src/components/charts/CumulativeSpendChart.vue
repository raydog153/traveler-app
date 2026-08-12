<template>
  <div class="chart-box">
    <Line :data="chartData" :options="options" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'

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
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { boxWidth: 12 } } },
  scales: {
    x: { type: 'time', time: { unit: 'quarter' }, grid: { color: '#1c2733' } },
    y: { grid: { color: '#1c2733' }, title: { display: true, text: 'Cumulative $' } },
  },
}
</script>

<style scoped>
.chart-box {
  height: 340px;
}
</style>
