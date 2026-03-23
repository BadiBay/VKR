<script setup>
import { VueFinalModal } from 'vue-final-modal'
import { computed, ref, watch, onMounted } from 'vue'
import axios from 'axios'
import { marked } from 'marked' // ПТ-8

const props = defineProps({ 
  cluster: Object,
  projectUrl: String 
})

// --- Состояние ---
const isAnalyzing = ref(false);     
const isGeneratingAi = ref(false);  
const isMetaLoading = ref(false);   

const aiContent = ref('');          
const generatedMeta = ref('');      
const competitorData = ref(null);   

const roles = ref([]);
const selectedRole = ref(null);
const customLSI = ref('');
const isPreviewMode = ref(false); // Для переключения режимов
const activeTab = ref('tz'); // 'tz' | 'article'

onMounted(async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/ai-roles/');
    roles.value = res.data;
  } catch(e) {}
});

watch(() => props.cluster, () => {
  aiContent.value = '';
  generatedMeta.value = '';
  competitorData.value = null;
  customLSI.value = '';
  isPreviewMode.value = false;
});

const mainKeyword = computed(() => {
  if (!props.cluster?.keywords?.length) return '';
  return [...props.cluster.keywords].sort((a,b) => b.volume - a.volume)[0].query;
});

async function analyzeCompetitors() {
  isAnalyzing.value = true;
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/projects/analyze_competitors/', {
      query: mainKeyword.value
    });
    competitorData.value = res.data;
  } catch (e) {
    alert("Не удалось проанализировать конкурентов.");
  } finally {
    isAnalyzing.value = false;
  }
}

async function generateArticle() {
  isGeneratingAi.value = true;
  const pathParts = window.location.pathname.split('/');
  const projectId = pathParts[pathParts.length - 1] || pathParts[pathParts.length - 2];

  try {
    const res = await axios.post(`http://127.0.0.1:8000/api/projects/${projectId}/generate_content/`, {
      cluster_id: props.cluster.id,
      role_id: selectedRole.value,
      custom_lsi: customLSI.value
    });
    aiContent.value = res.data.content;
    isPreviewMode.value = false; // Открываем редактор по умолчанию
  } catch (e) {
    alert("Ошибка генерации. Проверьте консоль Django.");
  } finally {
    isGeneratingAi.value = false;
  }
}

async function generateMeta() {
  isMetaLoading.value = true;
  const pathParts = window.location.pathname.split('/');
  const projectId = pathParts[pathParts.length - 1] || pathParts[pathParts.length - 2];

  try {
    const res = await axios.post(`http://127.0.0.1:8000/api/projects/${projectId}/generate_meta/`, {
      keyword: mainKeyword.value,
      role_id: selectedRole.value
    });
    generatedMeta.value = res.data.content;
  } catch (e) {
    alert("Ошибка генерации мета-тегов.");
  } finally {
    isMetaLoading.value = false;
  }
}

const downloadDocx = async (type) => {
  const pathParts = window.location.pathname.split('/');
  const projectId = pathParts[pathParts.length - 1] || pathParts[pathParts.length - 2];
  
  const content = type === 'article' ? aiContent.value : finalText.value;
  if (!content) return alert("Нет контента для скачивания");

  const lsiStr = competitorData.value?.lsi_words ? competitorData.value.lsi_words.join(', ') : '';
  const payload = {
    cluster_id: props.cluster.id,
    doc_type: type,
    content: content,
    meta: generatedMeta.value || '',
    lsi: type === 'tz' ? lsiStr : '' 
  };

  try {
    const res = await axios.post(`http://127.0.0.1:8000/api/projects/${projectId}/download_docx/`, payload, {
      responseType: 'blob'
    });
    
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${type === 'article' ? 'Article' : 'TZ'}_${props.cluster.name}.docx`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (e) {
    alert("Ошибка скачивания DOCX.");
  }
};

const finalText = computed(() => {
  if (!props.cluster) return 'Загрузка...';

  const sortedKw = [...props.cluster.keywords].sort((a, b) => b.volume - a.volume);
  const mainKeys = sortedKw.slice(0, 5); 
  const additionalKeys = sortedKw.slice(5); 

  let volMin = 3000;
  let volMax = 5000;
  let structureBlock = "1. Введение\n2. Виды и характеристики\n3. Преимущества\n4. Как выбрать\n5. Заключение";
  let competitorsInfo = "Анализ не проводился (Нажмите '🔍 Анализ')";

  if (competitorData.value) {
    const avg = competitorData.value.avg_text_length;
    volMin = Math.floor(avg * 0.9);
    volMax = Math.floor(avg * 1.1);
    if (competitorData.value.competitors_structure) structureBlock = competitorData.value.competitors_structure;
    competitorsInfo = competitorData.value.competitors_urls.join('\n');
  }

  return `ТЗ ДЛЯ КОПИРАЙТЕРА НА SEO-ТЕКСТ

=========================================
1. ВВОДНАЯ ИНФОРМАЦИЯ
=========================================
Тема: ${props.cluster.name}
Главный запрос: ${mainKeyword.value}
Страница размещения: ${props.projectUrl || 'https://...'}
Стиль: Коммерческий, экспертный, полезный для читателя.

=========================================
2. ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ
=========================================
Объем текста: от ${volMin} до ${volMax} символов без пробелов.
Уникальность: от 85% (text.ru).
Форматирование:
- Текст разбивается на абзацы (одна мысль = один абзац).
- Обязательно использовать подзаголовки H2 и H3.
- Использовать маркированные и нумерованные списки.
- Избегать сложных конструкций и "воды".

=========================================
3. СТРУКТУРА ТЕКСТА (На основе ТОП-3)
=========================================
Ниже приведены заголовки конкурентов. Составьте итоговую структуру, используя лучшие блоки:

${structureBlock}

=========================================
4. ГЛАВНЫЕ КЛЮЧЕВЫЕ СЛОВА
=========================================
Обязательно вписать в текст (можно менять окончания):

${mainKeys.map(k => `[ ] ${k.query} (Vol: ${k.volume})`).join('\n')}

=========================================
5. ДОПОЛНИТЕЛЬНЫЕ СЛОВА (Контекст)
=========================================
Использовать для раскрытия темы:

${additionalKeys.map(k => `- ${k.query}`).join(', ')}

=========================================
6. АНАЛИЗ КОНКУРЕНТОВ
=========================================
Ссылки на сайты из ТОПа:
${competitorsInfo}
`;
})

// Новые Computed-свойства для ПТ-8 и ПТ-9
const parsedContent = computed(() => marked(aiContent.value));
const currentLength = computed(() => aiContent.value.length);

function copyToClipboard() {
  navigator.clipboard.writeText(aiContent.value || finalText.value).then(() => alert('Текст скопирован!'));
}
</script>

<template>
  <VueFinalModal
    class="vfm-overlay"
    overlay-transition="vfm-fade"
    content-transition="vfm-fade"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="actual-box">
      
      <div class="box-header">
        <h2>{{ cluster?.name || 'ТЗ и Статья' }}</h2>
        
        <div class="header-controls">
          <!-- БЛОК ПАРАМЕТРОВ AI -->
          <div class="ai-controls">
            <select v-model="selectedRole">
              <option :value="null">-- Роль ИИ --</option>
              <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
            </select>
            <input type="text" v-model="customLSI" placeholder="Доп. LSI (напр: купить, срочно)">
          </div>

          <div class="actions">
            <button @click="generateArticle" class="btn btn-magic" :disabled="isGeneratingAi">
              {{ isGeneratingAi ? 'Пишу...' : '✨ Написать статью' }}
            </button>
            <button @click="analyzeCompetitors" class="btn btn-blue" :disabled="isAnalyzing">
              {{ isAnalyzing ? 'Анализ...' : '🔍 Анализ' }}
            </button>
            <button @click="generateMeta" class="btn btn-yellow" :disabled="isMetaLoading">
              {{ isMetaLoading ? '...' : '🏷 Meta' }}
            </button>

            <div class="divider"></div>
            <button @click="downloadDocx('tz')" class="btn btn-grey">DOCX ТЗ</button>
            <button @click="downloadDocx('article')" class="btn btn-grey" :disabled="!aiContent">DOCX Статья</button>
            <button @click="copyToClipboard" class="btn btn-green">Копировать</button>
            <button @click="$emit('update:modelValue', false)" class="btn btn-red">X</button>
          </div>
        </div>
      </div>
      
      <div class="box-body">
        <div class="main-tabs">
          <button @click="activeTab = 'tz'" :class="{active: activeTab === 'tz'}">ТЗ для копирайтера</button>
          <button @click="activeTab = 'article'" :class="{active: activeTab === 'article'}">Готовая статья</button>
        </div>

        <div v-if="isAnalyzing" class="loader-overlay">
          Изучаем ТОП-3 конкурентов (DuckDuckGo)...<br>Считаем символы и структуру...
        </div>
        <div v-if="isGeneratingAi" class="loader-overlay purple">
          🧠 GigaChat пишет статью...<br>Это займет 10-20 секунд.
        </div>
        <div v-if="isMetaLoading" class="loader-overlay yellow">
          Генерируем Title и Description...
        </div>

        <div v-if="generatedMeta && activeTab === 'tz'" class="meta-panel">
          <div class="panel-header">
            <strong>SEO-теги (GigaChat):</strong>
            <button @click="generatedMeta = ''">×</button>
          </div>
          <pre>{{ generatedMeta }}</pre>
        </div>

        <div v-if="competitorData?.lsi_words && activeTab === 'tz'" class="lsi-panel">
          <div class="panel-header">
            <span><strong>💡 LSI (TF-IDF анализ):</strong> {{ competitorData.lsi_words.join(', ') }}</span>
            <button @click="competitorData.lsi_words = null">×</button>
          </div>
        </div>

        <!-- ИНТЕРАКТИВНЫЙ РЕДАКТОР СТАТЬИ -->
        <div v-show="activeTab === 'article'" class="editor-container">
            <div v-if="!aiContent" class="empty-article">
                <p>Статья еще не сгенерирована.</p>
                <button @click="generateArticle" class="btn btn-magic" :disabled="isGeneratingAi">Сгенерировать статью</button>
            </div>
            <template v-else>
              <div class="editor-tabs">
                  <div>
                     <button @click="isPreviewMode=false" :class="{active: !isPreviewMode}">📝 Редактор (Raw)</button>
                     <button @click="isPreviewMode=true" :class="{active: isPreviewMode}">👀 Предпросмотр</button>
                  </div>
                  <!-- ПТ-9: ИНСТРУМЕНТ СРАВНЕНИЯ ОБЪЕМА -->
                  <div class="volume-indicator">
                      Символов: <strong>{{ currentLength }}</strong>
                      <span v-if="competitorData">
                          / Конкуренты (ТОП): ~{{ competitorData.avg_text_length }}
                          <span v-if="currentLength >= competitorData.avg_text_length * 0.9" style="color: #10b981;">(Ок ✓)</span>
                          <span v-else style="color: #ef4444;">(Мало ⚠️)</span>
                      </span>
                      <span v-else style="color: #9ca3af; font-weight: normal; font-size: 0.9em;">(Анализ для сравнения)</span>
                  </div>
              </div>
              
              <textarea v-if="!isPreviewMode" v-model="aiContent"></textarea>
              <div v-else class="markdown-preview" v-html="parsedContent"></div>
            </template>
        </div>

        <textarea v-show="activeTab === 'tz'" readonly>{{ finalText }}</textarea>
      </div>

    </div>
  </VueFinalModal>
</template>

<style>
/* ОБЩИЕ СТИЛИ ОКНА */
.vfm-overlay {
  display: flex !important; justify-content: center !important; align-items: center !important;
  padding: 20px; background-color: rgba(15, 23, 42, 0.75); backdrop-filter: blur(4px);
}
.actual-box {
  background-color: var(--bg-surface); width: 1200px; max-width: 100%; height: 90vh;
  display: flex; flex-direction: column; border-radius: var(--radius-lg); box-shadow: var(--shadow-glass); overflow: hidden;
  border: 1px solid var(--border-color);
  transform-origin: center; animation: modalPop 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes modalPop {
  0% { transform: scale(0.95); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

/* ШАПКА */
.box-header {
  display: flex; flex-direction: column; align-items: stretch; padding: 15px 20px;
  border-bottom: 1px solid var(--border-color); background: var(--bg-surface); gap: 10px;
}
.box-header h2 { margin: 0; font-size: 1.25rem; color: var(--text-main); font-weight: 700; width: 100%; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.header-controls { display: flex; flex-direction: column; gap: 10px; align-items: center; width: 100%; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; justify-content: center; }
.divider { width: 1px; height: 30px; background: var(--border-color); margin: 0 5px; }

.ai-controls {
  display: flex; gap: 8px; align-items: center; background: var(--bg-input); padding: 4px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);
}
.ai-controls select, .ai-controls input {
  padding: 6px 10px; border-radius: var(--radius-sm); border: 1px solid transparent; width: auto; font-size: 0.85rem;
}
.ai-controls select:focus, .ai-controls input:focus { border-color: var(--primary); }

/* ВКЛАДКИ (ТЗ / Статья) */
.main-tabs { display: flex; background: var(--bg-input); padding: 0 20px; border-bottom: 1px solid var(--border-color); gap: 10px; }
.main-tabs button { padding: 12px 20px; border: none; background: transparent; cursor: pointer; color: var(--text-muted); font-weight: 600; font-size: 1rem; border-bottom: 2px solid transparent; transition: all 0.2s; }
.main-tabs button:hover { color: var(--text-main); }
.main-tabs button.active { color: var(--primary); border-bottom-color: var(--primary); }

/* ПАНЕЛИ (META, LSI) */
.meta-panel { background: rgba(59, 130, 246, 0.1); padding: 15px 25px; border-bottom: 1px solid rgba(59, 130, 246, 0.2); color: var(--primary); font-size: 0.9rem; }
.meta-panel pre { white-space: pre-wrap; margin: 5px 0 0 0; font-family: monospace; }
.lsi-panel { background: rgba(245, 158, 11, 0.1); padding: 10px 25px; border-bottom: 1px solid rgba(245, 158, 11, 0.2); color: var(--warning); font-size: 0.9rem; }

.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
.panel-header button { background: transparent; border: none; color: inherit; font-size: 1.2rem; cursor: pointer; opacity: 0.7; font-weight: bold; padding: 0 5px; line-height: 1; }
.panel-header button:hover { opacity: 1; }

/* ТЕЛО */
.box-body { flex-grow: 1; padding: 0; position: relative; display: flex; flex-direction: column; background: var(--bg-base); min-height: 0; }
.box-body > textarea {
  flex-grow: 1; width: 100%; border: none; resize: none; padding: 25px;
  font-family: inherit; font-size: 14px; line-height: 1.6;
  background-color: transparent; color: var(--text-main); outline: none;
}

/* РЕДАКТОР СТАТЬИ */
.editor-container { display: flex; flex-direction: column; flex-grow: 1; overflow: hidden; min-height: 0; }
.empty-article { display: flex; flex-direction: column; align-items: center; justify-content: center; flex-grow: 1; color: var(--text-muted); gap: 15px; }
.editor-tabs { display: flex; justify-content: space-between; align-items: center; background: var(--bg-input); padding: 8px 20px; border-bottom: 1px solid var(--border-color); }
.editor-tabs button { padding: 6px 14px; border: none; background: transparent; cursor: pointer; color: var(--text-muted); font-weight: bold; border-radius: var(--radius-sm); transition: all 0.2s; }
.editor-tabs button:hover { color: var(--text-main); }
.editor-tabs button.active { background: var(--bg-surface); color: var(--primary); box-shadow: var(--shadow-sm); border: 1px solid var(--border-color); }
.volume-indicator { font-size: 0.9em; color: var(--text-muted); font-weight: 500; }

.editor-container textarea {
  flex-grow: 1; border: none; resize: none; padding: 30px; font-family: inherit; font-size: 15px; line-height: 1.7; background: var(--bg-base); color: var(--text-main); outline: none;
}
.markdown-preview {
  flex-grow: 1; padding: 30px; background: var(--bg-surface); color: var(--text-main); overflow-y: auto; font-family: inherit; line-height: 1.7; font-size: 1.05rem; min-height: 0;
}
.markdown-preview h1, .markdown-preview h2, .markdown-preview h3 { color: var(--text-main); margin-top: 1.5em; margin-bottom: 0.5em; }
.markdown-preview p { margin-bottom: 1.2em; }
.markdown-preview ul { padding-left: 20px; margin-bottom: 1.2em; }
.markdown-preview strong { color: var(--text-main); font-weight: 700; }

/* ЛОАДЕРЫ */
.loader-overlay {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  background: var(--bg-surface); color: var(--primary);
  display: flex; justify-content: center; align-items: center; text-align: center;
  font-weight: bold; font-size: 1.2rem; z-index: 10; opacity: 0.95;
  backdrop-filter: blur(2px);
}
.loader-overlay.purple { color: #8b5cf6; }
.loader-overlay.yellow { color: var(--warning); }
</style>