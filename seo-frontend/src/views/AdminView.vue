<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { RouterLink } from 'vue-router'

const API = 'http://127.0.0.1:8000/api'

const keys = ref([])
const logs = ref([])
const roles = ref([])

async function loadData() {
  const [resKeys, resLogs, resRoles] = await Promise.all([
    axios.get(`${API}/api-keys/`),
    axios.get(`${API}/api-logs/`),
    axios.get(`${API}/ai-roles/`)
  ])
  keys.value = resKeys.data
  logs.value = resLogs.data
  roles.value = resRoles.data
}

onMounted(() => loadData())

async function addKey() {
  const service = prompt("Сервис (gigachat, bukvarix):", "gigachat")
  const keyName = prompt("Название ключа:", "Мой GigaChat")
  const key = prompt("Значение ключа (Token):")
  if (keyName && key && service) {
    try {
      const name = `${service}: ${keyName}`
      await axios.post(`${API}/api-keys/`, { name, key })
      loadData()
    } catch(e) { alert("Ошибка добавления ключа") }
  }
}

async function deleteKey(id) {
  if (confirm("Точно удалить ключ?")) {
    await axios.delete(`${API}/api-keys/${id}/`)
    loadData()
  }
}

async function addRole() {
  const name = prompt("Название роли (Копирайтер):")
  const prompt_addition = prompt("Промпт (Действуй как профессиональный...):")
  if (name && prompt_addition) {
      try {
        await axios.post(`${API}/ai-roles/`, { name, prompt_addition })
        loadData()
      } catch(e) { alert("Ошибка добавления роли") }
  }
}

async function deleteRole(id) {
  if(confirm("Удалить роль?")) {
    await axios.delete(`${API}/ai-roles/${id}/`)
    loadData()
  }
}
</script>

<template>
  <div class="page content-fade-in">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
      <h1>Панель Администратора (Настройки)</h1>
      <RouterLink to="/" class="btn btn-grey">Вернуться к проектам</RouterLink>
    </div>

    <div class="grid">
      <!-- Роли AI -->
      <section class="card">
        <div class="card-header">
           <h2>🧠 Роли AI (Промпты)</h2>
           <button @click="addRole" class="btn btn-blue btn-sm">Добавить</button>
        </div>
        <table>
          <thead><tr><th>ID</th><th>Название</th><th>Промпт</th><th>Действие</th></tr></thead>
          <tbody>
            <tr v-for="r in roles" :key="r.id">
              <td>{{r.id}}</td><td>{{r.name}}</td>
              <td class="trunc" :title="r.prompt_addition">{{r.prompt_addition}}</td>
              <td><button @click="deleteRole(r.id)" class="btn btn-red btn-sm">🗑</button></td>
            </tr>
            <tr v-if="roles.length === 0"><td colspan="4" style="text-align: center; color: var(--text-muted);">Нет ролей</td></tr>
          </tbody>
        </table>
      </section>

      <!-- API Ключи -->
      <section class="card">
        <div class="card-header">
           <h2>🔑 API Ключи</h2>
           <button @click="addKey" class="btn btn-green btn-sm">Добавить</button>
        </div>
        <table>
          <thead><tr><th>ID</th><th>Название (Сервис)</th><th>Ключ</th><th>Действие</th></tr></thead>
          <tbody>
            <tr v-for="k in keys" :key="k.id">
              <td>{{k.id}}</td><td>{{k.name}}</td>
              <td class="trunc" :title="k.key">{{k.key}}</td>
              <td><button @click="deleteKey(k.id)" class="btn btn-red btn-sm">🗑</button></td>
            </tr>
            <tr v-if="keys.length === 0"><td colspan="4" style="text-align: center; color: var(--text-muted);">Нет ключей</td></tr>
          </tbody>
        </table>
      </section>
    </div>

    <!-- Логи -->
    <section class="card mt-20">
       <h2>🧾 Логи API (Расход токенов)</h2>
       <table>
          <thead><tr><th>Дата</th><th>Endpoint</th><th>Status</th><th>Токены</th><th>Время(мс)</th><th>IP</th></tr></thead>
          <tbody>
            <tr v-for="l in logs" :key="l.id">
              <td>{{ new Date(l.created_at).toLocaleString() }}</td>
              <td>{{l.endpoint}}</td>
              <td><span :class="l.status_code === 200 || l.status_code === 201 ? 'text-green' : 'text-red'">{{l.status_code}}</span></td>
              <td><strong>{{l.tokens_used}}</strong></td>
              <td>{{l.duration_ms}} ms</td>
              <td>{{l.user_ip || '-'}}</td>
            </tr>
            <tr v-if="logs.length === 0"><td colspan="6" style="text-align: center; color: var(--text-muted);">Логов пока нет</td></tr>
          </tbody>
        </table>
    </section>

  </div>
</template>

<style scoped>
.page { padding: 20px 0; padding-bottom: 80px;}
h1 { margin: 0; font-size: 2rem; color: var(--text-main); font-weight: 700; letter-spacing: -0.5px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; align-items: start; }
.card { background: var(--bg-surface); padding: 20px 25px; border-radius: var(--radius-md); box-shadow: var(--shadow-md); border: 1px solid var(--border-color); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.card-header h2 { margin: 0; font-size: 1.25rem; color: var(--text-main); font-weight: 600; }
.mt-20 { margin-top: 20px; }

table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid var(--border-color); color: var(--text-main); }
th { background: var(--bg-input); color: var(--text-muted); font-weight: 600; }
.trunc { max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: help; }

.btn-sm { padding: 6px 10px; font-size: 0.85rem; border-radius: var(--radius-sm); }
.text-green { color: var(--success); font-weight: bold; }
.text-red { color: var(--danger); font-weight: bold; }

@media (max-width: 1024px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
