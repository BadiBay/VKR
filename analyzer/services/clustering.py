import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

# Модель загружается один раз при старте воркера Celery
MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
_model = None


def get_model():
    global _model
    if _model is None:
        print(f"⏳ Загрузка нейросетевой модели {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
        print("✅ Модель загружена!")
    return _model


def cluster_keywords(keywords: list[str], similarity_threshold=0.6):
    """Семантическая кластеризация ключевых слов на основе BERT-эмбеддингов."""
    if not keywords:
        return {}
    if len(keywords) < 2:
        return {keywords[0]: 0}

    model = get_model()
    embeddings = model.encode(keywords)

    # Нормализуем векторы для корректного косинусного расстояния
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    cosine_distance_matrix = 1 - cosine_similarity(embeddings)
    dist_threshold = 1 - similarity_threshold

    clustering_model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=dist_threshold,
        metric='precomputed',
        linkage='average'
    )
    clustering_model.fit(cosine_distance_matrix)

    labels = clustering_model.labels_
    results = {keyword: int(labels[i]) for i, keyword in enumerate(keywords)}

    n_clusters = len(set(labels))
    print(f"📊 Кластеризация завершена. Фраз: {len(keywords)}, Кластеров: {n_clusters}")

    return results