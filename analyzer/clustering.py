import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

# Глобальная переменная для модели, чтобы не загружать её при каждом вызове функции.
# При запуске Celery она загрузится один раз в память воркера.
# paraphrase-multilingual-MiniLM-L12-v2 - лучшая легкая модель для русского языка (и других).
MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
_model = None

def get_model():
    """Ленивая загрузка модели"""
    global _model
    if _model is None:
        print(f"⏳ Загрузка нейросетевой модели {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
        print("✅ Модель загружена!")
    return _model

def cluster_keywords(keywords: list[str], similarity_threshold=0.6):
    """
    Семантическая кластеризация на основе BERT.
    
    :param keywords: Список запросов
    :param similarity_threshold: Порог схожести (0.0 - 1.0). 
           0.65 - хороший баланс для SEO (чем выше, тем дробнее кластеры).
    """
    if not keywords:
        return {}
    
    # Если ключей совсем мало, нет смысла запускать тяжелую артиллерию
    if len(keywords) < 2:
        return {keywords[0]: 0}

    # 1. Получаем модель
    model = get_model()

    # 2. Векторизация (Превращаем текст в смысловые векторы)
    # Это самая долгая часть, может занять пару секунд на 1000 ключей
    embeddings = model.encode(keywords)

    # 3. Нормализация векторов (важно для косинусного расстояния)
    # В sentence-transformers они обычно уже нормализованы, но для надежности:
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    # 4. Иерархическая кластеризация
    # Мы используем 'precomputed' дистанцию, чтобы работать с косинусным сходством
    # Косинусное расстояние = 1 - Косинусное сходство
    cosine_distance_matrix = 1 - cosine_similarity(embeddings)
    
    # Превращаем порог схожести в порог дистанции
    dist_threshold = 1 - similarity_threshold

    clustering_model = AgglomerativeClustering(
        n_clusters=None,             # Мы не знаем кол-во кластеров заранее
        distance_threshold=dist_threshold, # Разбивай, если дистанция больше этого
        metric='precomputed',        # Используем нашу матрицу
        linkage='average'            # 'average' обычно дает самые чистые SEO кластеры
    )

    clustering_model.fit(cosine_distance_matrix)
    
    # 5. Формируем результат
    results = {}
    
    # clustering_model.labels_ содержит ID кластера для каждого слова по порядку
    labels = clustering_model.labels_
    
    for i, keyword in enumerate(keywords):
        cluster_id = int(labels[i])
        results[keyword] = cluster_id
        
    # Выводим немного статистики в лог
    n_clusters = len(set(labels))
    print(f"📊 Кластеризация завершена. Фраз: {len(keywords)}, Кластеров: {n_clusters}")
    
    return results