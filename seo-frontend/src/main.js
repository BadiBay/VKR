//import './assets/main.css'

import { createApp } from 'vue'
import { createVfm } from 'vue-final-modal' // <-- Импорт библиотеки модалок
import 'vue-final-modal/style.css'          // <-- Импорт стилей модалок

import App from './App.vue'
import router from './router'

const app = createApp(App)
const vfm = createVfm() // <-- Создание экземпляра

app.use(router)
app.use(vfm) // <-- Подключение к приложению

app.mount('#app')