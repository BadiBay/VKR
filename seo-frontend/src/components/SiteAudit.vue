<script setup>
import { computed } from 'vue';

const props = defineProps({ auditData: Object });

const scoreColor = computed(() => {
  const s = props.auditData.score;
  // Get CSS Variables from active theme
  const style = getComputedStyle(document.body);
  if (s >= 90) return style.getPropertyValue('--success').trim() || '#10b981';
  if (s >= 50) return style.getPropertyValue('--warning').trim() || '#f59e0b';
  return style.getPropertyValue('--danger').trim() || '#ef4444'; 
});
</script>

<template>
  <div class="audit-card fade-in">
    <div class="score-section">
      <div class="score-circle" :style="{ borderColor: scoreColor }">
        <span class="score-num" :style="{ color: scoreColor }">{{ auditData.score }}</span>
        <span class="score-label">Health Score</span>
      </div>
    </div>
    
    <div class="checks-list">
      <div 
        v-for="(check, idx) in auditData.checks" 
        :key="idx" 
        class="check-item"
        :style="{ animationDelay: (idx * 0.1) + 's' }"
      >
        <span class="icon">{{ check.status ? '✅' : '❌' }}</span>
        <div class="info">
          <strong>{{ check.name }}</strong>
          <small>{{ check.msg }}</small>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.audit-card {
  display: flex;
  background: var(--bg-surface);
  padding: 25px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  margin-bottom: 20px;
  gap: 30px;
  align-items: center;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  border: 8px solid var(--border-color);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
.score-num { font-size: 2.5rem; font-weight: bold; line-height: 1; }
.score-label { font-size: 0.85rem; color: var(--text-muted); margin-top: 5px; font-weight: 500;}

.checks-list { flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.check-item { 
  display: flex; align-items: center; gap: 10px;
  animation: fadeIn 0.4s ease-out forwards; opacity: 0;
}
.icon { font-size: 1.2rem; }
.info { display: flex; flex-direction: column; }
.info strong { font-size: 0.95rem; color: var(--text-main); }
.info small { color: var(--text-muted); font-size: 0.85rem; margin-top: 2px;}
</style>