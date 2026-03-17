<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { RouterLink } from 'vue-router';

const API_URL = 'http://127.0.0.1:8000/api';
const projects = ref([]);
const newName = ref('');
const newUrl = ref('');

async function loadProjects() {
  try {
    const res = await axios.get(`${API_URL}/projects/`);
    projects.value = res.data;
  } catch (e) {
    console.error(e);
  }
}

async function addProject() {
  if (!newName.value || !newUrl.value) return;
  try {
    await axios.post(`${API_URL}/projects/`, { name: newName.value, url: newUrl.value });
    newName.value = '';
    newUrl.value = '';
    loadProjects();
  } catch (e) {
    alert('Ошибка при создании проекта');
  }
}

onMounted(loadProjects);
</script>

<template>
  <div class="home fade-in">
    <div class="header-section">
      <h1 class="page-title">Список проектов</h1>
      <RouterLink to="/admin_panel" class="btn btn-grey">⚙️ Настройки AI/API</RouterLink>
    </div>
    
    <div class="card form fade-in stagger-1">
      <input v-model="newName" placeholder="Название проекта" />
      <input v-model="newUrl" placeholder="URL сайта (https://...)" />
      <button class="btn btn-blue" @click="addProject">➕ Создать</button>
    </div>

    <div v-if="projects.length" class="list">
      <div v-for="(p, i) in projects" :key="p.id" class="card project" :style="{ animationDelay: (i * 0.05) + 's' }">
        <div class="project-info">
          <strong class="project-name">{{ p.name }}</strong>
          <span class="project-url">{{ p.url }}</span>
        </div>
        <RouterLink :to="`/project/${p.id}`" class="btn btn-green">Открыть &rarr;</RouterLink>
      </div>
    </div>
    <div v-else class="empty-state fade-in stagger-2">
      <div class="empty-icon">📁</div>
      <p>Проектов пока нет. Создайте первый!</p>
    </div>
  </div>
</template>

<style scoped>
.home { max-width: 750px; margin: 20px auto; }
.header-section { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
.page-title { margin: 0; font-size: 1.8rem; font-weight: 700; letter-spacing: -0.5px; color: var(--text-main); }

.card { 
  background: var(--bg-surface); 
  padding: 20px 25px; 
  border-radius: var(--radius-md); 
  margin-bottom: 12px; 
  box-shadow: var(--shadow-sm); 
  border: 1px solid var(--border-color);
  transition: all 0.2s ease;
}
.form { display: flex; gap: 15px; margin-bottom: 30px; flex-wrap: wrap; }
.form input { padding: 12px 15px; flex: 1; min-width: 200px; border-radius: var(--radius-sm); }
.form button { white-space: nowrap; }

.project { 
  display: flex; justify-content: space-between; align-items: center; 
  animation: fadeIn 0.4s ease-out forwards;
  opacity: 0;
}
.project:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary);
}
.project-info { display: flex; flex-direction: column; gap: 4px; }
.project-name { font-size: 1.15rem; color: var(--text-main); }
.project-url { color: var(--text-muted); font-size: 0.9rem; }

.empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); }
.empty-icon { font-size: 3.5rem; margin-bottom: 15px; opacity: 0.8; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1)); }
</style>