<script setup>
import { RouterView, RouterLink } from 'vue-router'
import { ref, onMounted } from 'vue'

const isDarkMode = ref(false)

function toggleTheme() {
  isDarkMode.value = !isDarkMode.value
  updateTheme()
}

function updateTheme() {
  if (isDarkMode.value) {
    document.body.classList.add('dark-theme')
    localStorage.setItem('theme', 'dark')
  } else {
    document.body.classList.remove('dark-theme')
    localStorage.setItem('theme', 'light')
  }
}

onMounted(() => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    isDarkMode.value = true
  }
  updateTheme()
})
</script>

<template>
  <div class="app-container">
    <header class="app-header fade-in">
      <div class="header-logo">
        <RouterLink to="/">
          <span class="logo-icon">🚀</span>
          <strong>SEO AI Tool</strong>
        </RouterLink>
      </div>
      <div class="header-actions">
        <!-- Кнопка переключения темы -->
        <button class="theme-toggle" @click="toggleTheme" :title="isDarkMode ? 'Светлая тема' : 'Темная тема'">
          <span class="theme-icon">{{ isDarkMode ? '☀️' : '🌙' }}</span>
        </button>
      </div>
    </header>

    <main class="app-main fade-in stagger-1">
      <RouterView />
    </main>
  </div>
</template>

<style>
/* Импортируем нашу дизайн-систему */
@import './assets/theme.css';

.app-container {
  max-width: 1300px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
  margin-bottom: 30px;
  border-bottom: 1px solid var(--border-color);
}

.header-logo a {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text-main);
  font-size: 1.4rem;
  letter-spacing: -0.5px;
}

.logo-icon {
  font-size: 1.8rem;
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
}

.theme-toggle {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: var(--shadow-sm);
}

.theme-toggle:hover {
  transform: rotate(15deg) scale(1.1);
  box-shadow: var(--shadow-md);
  border-color: var(--primary);
}

.theme-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.app-main {
  flex-grow: 1;
}
</style>