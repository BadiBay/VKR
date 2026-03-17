<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import axios from 'axios';
import { ModalsContainer } from 'vue-final-modal';

import ClusterChart from '../components/ClusterChart.vue';
import ReportModal from '../components/ReportModal.vue';
import SiteAudit from '../components/SiteAudit.vue';

const API = 'http://127.0.0.1:8000/api';
const route = useRoute();
const projectId = route.params.id;

const project = ref(null);
const showModal = ref(false);
const selectedCluster = ref(null);
const auditResults = ref(null);

const draggedKeyword = ref(null);
const fileInput = ref(null);

const loading = reactive({
  page: true,
  fetch: false,
  clustering: false,
  refresh: false,
  audit: false
});

const progress = reactive({
  show: false,
  percent: 0,
  text: ''
});

async function load(isRefreshBtn = false) {
  if (isRefreshBtn) loading.refresh = true;
  try {
    const res = await axios.get(`${API}/projects/${projectId}/`);
    project.value = res.data;
  } catch (e) { 
    console.error(e);
    if (isRefreshBtn) alert("Не удалось обновить данные.");
  } finally {
    loading.page = false;
    loading.refresh = false;
  }
}

async function runAudit() {
  loading.audit = true;
  try {
    const res = await axios.get(`${API}/projects/${projectId}/audit/`);
    auditResults.value = res.data;
    alert("Аудит успешно сохранен в историю.");
  } catch (e) {
    alert("Ошибка аудита. Проверьте доступность сайта.");
  } finally {
    loading.audit = false;
  }
}

async function checkPosition(cluster) {
  const btnId = `btn-pos-${cluster.id}`;
  const btn = document.getElementById(btnId);
  const originalText = btn ? btn.innerText : '🎯 Позиция';
  
  if(btn) { btn.innerText = "⏳..."; btn.disabled = true; }
  try {
    const kw = cluster.keywords[0].query;
    const res = await axios.post(`${API}/projects/${projectId}/check_position/`, { query: kw });
    const pos = res.data.position;
    const url = res.data.found_url;
    alert(`Ключ: "${kw}"\n\nПозиция в Google: ${pos}\n${url ? 'URL: ' + url : ''}`);
  } catch(e) {
    alert("Не удалось проверить позицию.");
  } finally {
    if(btn) { btn.innerText = originalText; btn.disabled = false; }
  }
}

async function run(task) {
  if (task === 'clustering') {
    loading.clustering = true;
    try {
      const res = await axios.post(`${API}/projects/${projectId}/run_clustering/`);
      if (res.data.task_id) pollTaskStatus(res.data.task_id);
    } catch (e) {
      alert("Ошибка запуска кластеризации.");
      loading.clustering = false;
    }
  } else if (task === 'fetch') {
    loading.fetch = true;
    try {
      await axios.post(`${API}/projects/${projectId}/run_fetch/`);
      setTimeout(async () => { await load(); loading.fetch = false; }, 2000);
    } catch (e) {
      alert("Ошибка запуска сбора.");
      loading.fetch = false;
    }
  }
}

async function pollTaskStatus(taskId) {
  progress.show = true;
  progress.percent = 0;
  progress.text = "Инициализация...";
  const intervalId = setInterval(async () => {
    try {
      const res = await axios.get(`${API}/task_status/${taskId}/`);
      const data = res.data;
      progress.percent = data.percent || 0;
      progress.text = data.process || 'Обработка...';
      if (data.state === 'SUCCESS' || data.state === 'FAILURE') {
        clearInterval(intervalId);
        if (data.state === 'SUCCESS') {
          progress.percent = 100;
          progress.text = "Готово!";
          setTimeout(() => { progress.show = false; loading.clustering = false; load(); }, 1000);
        } else {
          alert(`Ошибка: ${data.process}`);
          progress.show = false; loading.clustering = false;
        }
      }
    } catch (e) {
      clearInterval(intervalId);
      progress.show = false; loading.clustering = false;
    }
  }, 1000);
}

// Новые функции
async function triggerImport() {
  fileInput.value.click();
}
async function onFileChange(e) {
  const file = e.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  loading.fetch = true;
  try {
    const res = await axios.post(`${API}/projects/${projectId}/import_keywords/`, formData);
    alert(res.data.status);
    await load(false);
  } catch(err) {
    alert(err.response?.data?.error || 'Ошибка импорта');
  }
  loading.fetch = false;
  e.target.value = null; // reset
}

async function massDelete() {
  const minVol = prompt("Удалить ключи с частотностью МЕНЬШЕ:", "10");
  const stopWords = prompt("Удалить ключи по стоп-словам (через запятую):", "дешево, бесплатно, б/у");
  if (minVol === null && stopWords === null) return;
  
  const filters = {};
  if (minVol) filters.min_volume = parseInt(minVol);
  if (stopWords) filters.stop_words = stopWords.split(',').map(s => s.trim()).filter(Boolean);
  
  loading.refresh = true;
  try {
    const res = await axios.post(`${API}/projects/${projectId}/mass_delete/`, { filters });
    alert(res.data.status);
    await load(false);
  } catch(e) { alert("Ошибка при удалении"); }
  loading.refresh = false;
}

// Cluster UI
async function resetClusters(onlyDrafts=false) {
  if(!confirm(`Удалить ${onlyDrafts ? 'черновики кластеров' : 'все кластеры'}? Ключевые слова останутся в проекте как нераспределенные.`)) return;
  loading.refresh = true;
  try {
    const res = await axios.post(`${API}/projects/${projectId}/reset_clusters/`, { only_drafts: onlyDrafts });
    alert(res.data.status);
    await load(false);
  } catch(e) { alert("Ошибка при сбросе"); }
  loading.refresh = false;
}

async function clearProject() {
  if(!confirm("Уверены, что хотите полностью очистить проект? Это безвозвратно удалит ВСЕ ключи и кластеры!")) return;
  loading.refresh = true;
  try {
    const res = await axios.post(`${API}/projects/${projectId}/clear_project/`);
    alert(res.data.status);
    await load(false);
  } catch(e) { alert("Ошибка при очистке"); }
  loading.refresh = false;
}

async function createCluster() {
  const name = prompt("Название кластера:", "Новый кластер");
  if(!name) return;
  try {
    await axios.post(`${API}/clusters/`, { name, project: projectId, status: 'draft' });
    load();
  } catch(e) { alert("Ошибка") }
}

async function renameCluster(c) {
  if (c.id === 'uncategorized') return;
  const name = prompt("Новое название:", c.name);
  if(!name || name === c.name) return;
  try {
    await axios.patch(`${API}/clusters/${c.id}/`, { name });
    load();
  } catch(e) { alert("Ошибка") }
}

async function approveCluster(c) {
  if (c.id === 'uncategorized') return;
  const newStatus = c.status === 'ready' ? 'draft' : 'ready';
  try {
    await axios.post(`${API}/clusters/${c.id}/change_status/`, { status: newStatus });
    load();
  } catch(e) { alert("Ошибка") }
}

function onDragStart(k, clusterId, event) {
  draggedKeyword.value = { keyword: k, from: clusterId };
  event.dataTransfer.effectAllowed = 'move';
}

async function onDrop(toClusterId) {
  if (!draggedKeyword.value) return;
  const { keyword, from } = draggedKeyword.value;
  if (from === toClusterId) {
    draggedKeyword.value = null;
    return;
  }
  
  try {
    if (toClusterId === 'uncategorized') {
      await axios.post(`${API}/projects/${projectId}/uncategorize_keyword/`, { keyword_id: keyword.id });
    } else {
      await axios.post(`${API}/clusters/${toClusterId}/move_keyword/`, { keyword_id: keyword.id });
    }
    // Update data reliably instead of risky local mutation
    await load(false);
  } catch(e) { 
    console.error(e);
    alert("Ошибка переноса");
  }
  draggedKeyword.value = null;
}

const clusters = computed(() => {
  if (!project.value) return [];
  const res = (project.value.clusters || []).map(c => {
    const kws = [...c.keywords].sort((a,b) => (b.volume||0) - (a.volume||0));
    return {
      id: c.id,
      name: c.name,
      status: c.status,
      keywords: kws,
      total_volume: kws.reduce((acc, k) => acc + (k.volume||0), 0)
    };
  });
  
  const uncatKws = (project.value.keywords || []).filter(k => k.cluster === null).sort((a,b) => (b.volume||0) - (a.volume||0));
  
  res.push({
    id: 'uncategorized',
    name: 'Без кластера (Нераспределенные)',
    status: null,
    keywords: uncatKws,
    total_volume: uncatKws.reduce((acc, k) => acc + (k.volume||0), 0)
  });
  
  return res.sort((a,b) => {
    if (a.id === 'uncategorized') return 1;
    if (b.id === 'uncategorized') return -1;
    return b.total_volume - a.total_volume;
  });
});

function openModal(c) { 
  selectedCluster.value = JSON.parse(JSON.stringify(c)); 
  showModal.value = true; 
}

onMounted(() => load(false));
</script>

<template>
  <div class="page">
    <RouterLink to="/" class="back-link">&larr; Назад к списку</RouterLink>
    
    <div v-if="loading.page" class="page-loader">
      <div class="spinner big"></div><p>Загрузка проекта...</p>
    </div>

    <div v-else-if="project" class="content-fade-in">
      <div class="header-section">
        <div class="header-top">
           <h1>{{ project.name }}</h1>
           <div class="controls">
              <input type="file" ref="fileInput" accept=".csv, .xlsx" style="display: none" @change="onFileChange">
              <button @click="triggerImport" class="btn btn-blue" :disabled="loading.fetch"><span v-if="!loading.fetch">📥 Импорт ключей</span><span v-else class="btn-content"><div class="spinner"></div> Загрузка...</span></button>
              
              <button @click="run('fetch')" class="btn btn-blue" :disabled="loading.fetch || loading.clustering || progress.show">
                <span v-if="!loading.fetch">1. Сбор (Букварикс)</span>
                <span v-else class="btn-content"><div class="spinner"></div> Сбор...</span>
              </button>

              <button @click="run('clustering')" class="btn btn-green" :disabled="loading.clustering || loading.fetch || progress.show">
                <span v-if="!loading.clustering">2. AI-Кластеризация</span>
                <span v-else class="btn-content"><div class="spinner"></div> Запуск...</span>
              </button>

              <button @click="massDelete" class="btn btn-grey" :disabled="loading.refresh">🗑 Мусор</button>

              <button @click="resetClusters(false)" class="btn btn-yellow" :disabled="loading.refresh">🧹 Сбросить кластеры</button>
              
              <button @click="clearProject" class="btn btn-red" :disabled="loading.refresh">🔥 Очистить проект</button>

              <button @click="load(true)" class="btn btn-grey" :disabled="loading.refresh || progress.show">
                <span v-if="!loading.refresh">Обновить</span><span v-else class="spinner"></span>
              </button>
           </div>
        </div>

        <div v-if="project.url" class="url-link"><a :href="project.url" target="_blank">{{ project.url }}</a></div>

        <div class="audit-block">
          <div v-if="!auditResults">
            <button @click="runAudit" class="btn btn-purple" :disabled="loading.audit">
              {{ loading.audit ? 'Сканирование сайта...' : '🩺 Запустить Технический Аудит' }}
            </button>
          </div>
          <SiteAudit v-else :auditData="auditResults" />
        </div>
      </div>

      <div v-if="progress.show" class="progress-container">
        <div class="progress-info"><span class="progress-text">{{ progress.text }}</span><span class="progress-percent">{{ progress.percent }}%</span></div>
        <div class="progress-track"><div class="progress-fill" :style="{ width: progress.percent + '%' }"></div></div>
      </div>

      <ClusterChart v-if="clusters.length > 1" :clusters="clusters" />

      <div class="clusters-controls" style="margin-bottom: 20px;">
        <button @click="createCluster" class="btn btn-grey">➕ Создать кластер ручками</button>
      </div>

      <div class="clusters-list" @dragover.prevent @drop.self="onDrop('uncategorized')">
        <div v-if="clusters.length === 0" class="empty-state"><p>Ключевых слов пока нет. Запустите импорт или сбор.</p></div>

        <div v-for="c in clusters" :key="c.id" 
             class="cluster-card" 
             :class="{ 'drop-zone': true, 'is-draft': c.status === 'draft', 'is-ready': c.status === 'ready' }"
             @dragover.prevent 
             @drop.stop="onDrop(c.id)">
             
          <div class="cluster-header">
            <div class="cluster-title" @dblclick="renameCluster(c)" style="cursor: pointer;" title="Кликните дважды чтобы переименовать">
                <h3>{{ c.name }} <span class="cluster-id">#{{ c.id }}</span></h3>
                <span class="vol">Vol: {{ c.total_volume }}</span>
                <span v-if="c.status === 'draft'" class="badge badge-draft">Черновик</span>
                <span v-if="c.status === 'ready'" class="badge badge-ready">Готов</span>
            </div>
            
            <div class="cluster-actions">
                <button v-if="c.id !== 'uncategorized'" @click="approveCluster(c)" class="btn-small" :class="{'btn-green': c.status==='draft', 'btn-grey': c.status==='ready'}">
                    {{ c.status === 'ready' ? 'Отозвать' : '✔ Утвердить' }}
                </button>
                <button v-if="c.id!=='uncategorized' && c.keywords.length > 0" :id="`btn-pos-${c.id}`" @click="checkPosition(c)" class="btn-small btn-orange">🎯 Позиция</button>
                <button v-if="c.id!=='uncategorized' && c.status==='ready'" @click="openModal(c)" class="btn-small btn-violet">ТЗ и Контент</button>
            </div>
          </div>
          
          <div class="keywords">
            <span v-for="k in c.keywords" :key="k.id" class="tag" draggable="true" @dragstart="onDragStart(k, c.id, $event)">
              {{ k.query }} <small>({{ k.volume }})</small>
            </span>
            <span v-if="c.keywords.length === 0" class="empty-text">Перетащите сюдя ключи...</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <ReportModal v-model="showModal" :cluster="selectedCluster" :project-url="project?.url" />
  <ModalsContainer />
</template>

<style scoped>
.page { padding-bottom: 60px; }
.back-link { display: inline-block; margin-bottom: 20px; color: var(--text-muted); font-weight: 500; text-decoration: none; transition: color 0.2s; }
.back-link:hover { color: var(--primary); }

.header-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 15px; }
h1 { color: var(--text-main); font-size: 2rem; letter-spacing: -0.5px; }

.controls { display: flex; gap: 10px; flex-wrap: wrap; }
.url-link { margin-bottom: 20px; font-size: 0.95rem; }
.audit-block { margin-bottom: 30px; }

/* Мы уже имеем .btn-* глобально, поэтому добавляем специфичные */
.btn-purple { background: var(--magic); width: 100%; color: white; padding: 12px; font-size: 1rem; border: none; border-radius: var(--radius-sm); font-weight: bold; cursor: pointer; transition: all 0.2s; }
.btn-purple:hover:not(:disabled) { transform: translateY(-2px); box-shadow: var(--shadow-sm); }
.btn-purple:disabled { opacity: 0.7; cursor: not-allowed; filter: grayscale(1); }

/* Clusters */
.cluster-card { background: var(--bg-surface); padding: 20px; border-radius: var(--radius-md); margin-bottom: 20px; box-shadow: var(--shadow-sm); border: 1px solid var(--border-color); transition: all 0.2s ease; }
.cluster-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.cluster-card.is-draft { border-left: 4px solid var(--warning); }
.cluster-card.is-ready { border-left: 4px solid var(--success); }

.cluster-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }
.cluster-title { display: flex; align-items: center; gap: 10px; }
.cluster-header h3 { margin: 0; font-size: 1.25rem; color: var(--text-main); }
.cluster-id { color: var(--text-muted); font-size: 0.9rem; font-weight: normal; }

.badge { font-size: 0.75rem; padding: 4px 10px; border-radius: 12px; font-weight: bold; }
.badge-draft { background: rgba(245, 158, 11, 0.15); color: var(--warning); }
.badge-ready { background: rgba(16, 185, 129, 0.15); color: var(--success); }
.vol { color: var(--success); font-size: 0.9em; background: rgba(16, 185, 129, 0.1); padding: 4px 8px; border-radius: var(--radius-sm); font-weight: 600; }

.cluster-actions { display: flex; gap: 8px; }
.btn-small { border: none; padding: 6px 14px; border-radius: var(--radius-sm); cursor: pointer; font-size: 0.85em; color: white; font-weight: 600; transition: transform 0.2s, filter 0.2s; }
.btn-small:hover { transform: translateY(-1px); filter: brightness(1.1); }
.btn-orange { background: #f97316; } .btn-violet { background: #8b5cf6; }

.keywords { display: flex; flex-wrap: wrap; gap: 8px; min-height: 45px; align-items: flex-start; }
.tag { background: var(--bg-input); border: 1px solid var(--border-color); padding: 6px 12px; border-radius: 20px; font-size: 0.9em; color: var(--text-main); cursor: grab; transition: all 0.2s; }
.tag:hover { border-color: var(--primary); background: var(--bg-surface); }
.tag:active { cursor: grabbing; transform: scale(0.95); opacity: 0.8; }
.tag small { color: var(--text-muted); margin-left: 4px; }
.empty-text { color: var(--text-muted); font-size: 0.9rem; font-style: italic; padding: 10px; border: 2px dashed var(--border-color); border-radius: var(--radius-sm); width: 100%; text-align: center; }
.drop-zone { min-height: 100px; }

/* Progress & Loading */
.progress-container { margin: 20px 0; padding: 25px; background: var(--bg-surface); border-radius: var(--radius-md); box-shadow: var(--shadow-md); border: 1px solid var(--border-color); }
.progress-info { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 1rem; font-weight: 600; color: var(--text-main); }
.progress-track { width: 100%; height: 14px; background: var(--bg-input); border-radius: 8px; overflow: hidden; }
.progress-fill { height: 100%; background-color: var(--success); transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1); }

.spinner { width: 16px; height: 16px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; }
.spinner.big { width: 40px; height: 40px; border-width: 4px; color: var(--primary); }
@keyframes spin { to { transform: rotate(360deg); } }
.page-loader { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px; gap: 15px; color: var(--text-muted); font-weight: 500; }
</style>