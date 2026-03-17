<script setup>
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'
import { computed } from 'vue'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const props = defineProps({ clusters: Array })

const chartData = computed(() => {
  const top = props.clusters.filter(c => c.id !== 'uncategorized').slice(0, 10);
  const color = getComputedStyle(document.body).getPropertyValue('--primary').trim() || '#3b82f6';
  
  return {
    labels: top.map(c => c.name),
    datasets: [{ label: 'Частотность', backgroundColor: color, data: top.map(c => c.total_volume) }]
  }
})

// Set generic chart colors for text so it matches dark mode implicitly
ChartJS.defaults.color = '#94a3b8';

const options = { responsive: true, maintainAspectRatio: false }
</script>

<template>
  <div class="chart-wrapper fade-in">
    <Bar :data="chartData" :options="options" />
  </div>
</template>

<style scoped>
.chart-wrapper { 
  height: 300px; 
  background: var(--bg-surface); 
  padding: 20px; 
  border-radius: var(--radius-md); 
  box-shadow: var(--shadow-sm); 
  border: 1px solid var(--border-color);
  margin-bottom: 25px; 
}
</style>