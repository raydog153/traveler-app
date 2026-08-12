<template>
  <div class="chart-box">
    <Line :data="chartData" :options="options" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'

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
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { type: 'time', time: { unit: 'quarter' }, grid: { color: '#1c2733' } },
    y: { grid: { color: '#1c2733' }, title: { display: true, text: '$/gal' } },
  },
}
</script>

<style scoped>
.chart-box {
  height: 340px;
}
</style>
