from celery import shared_task
import requests
import random
import time
import re
import urllib.parse
from bs4 import BeautifulSoup
from .models import Project, Keyword, Cluster
from .services.clustering import cluster_keywords
from .clickhouse_client import get_clickhouse_client, ensure_seo_logs_table_exists


# --- Сбор семантики: Bukvarix по домену ---
def get_domain_rankings(domain):
    print(f"🔎 Bukvarix: Анализ домена {domain}...")
    clean_domain = domain.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
    url = "https://api.bukvarix.com/v1/site/"
    params = {
        "api_key": "free",
        "q": clean_domain,
        "format": "json",
        "json_type": "array",
        "num": 300
    }
    results = []
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # item[0] — слово, item[4] — частотность
            for item in data:
                if len(item) > 4:
                    results.append({'keyword': item[0], 'volume': int(item[4])})
    except Exception as e:
        print(f"⚠️ Ошибка Bukvarix Domain API: {e}")
    return results


# --- Сбор семантики: Bukvarix по ключевому слову ---
def get_related_keywords(query):
    print(f"🔎 Bukvarix: Поиск по слову '{query}'...")
    encoded_query = urllib.parse.quote(query)
    url = f"http://api.bukvarix.com/v1/keywords/?q={encoded_query}&api_key=free&num=50"
    results = []
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            for line in lines:
                parts = line.split(';')
                if len(parts) >= 2:
                    try:
                        vol = int(parts[1].strip())
                        results.append({'keyword': parts[0].strip(), 'volume': vol})
                    except: pass
    except: pass
    return results


# --- Подсказки Google и YouTube ---
def get_google_suggestions(query):
    url = "http://google.com/complete/search"
    try:
        resp = requests.get(url, params={"client": "chrome", "q": query, "hl": "ru"}, timeout=2)
        if resp.status_code == 200: return resp.json()[1]
    except: pass
    return []

def get_youtube_suggestions(query):
    url = "http://suggestqueries.google.com/complete/search"
    try:
        resp = requests.get(url, params={"client": "firefox", "ds": "yt", "q": query, "hl": "ru"}, timeout=2)
        if resp.status_code == 200: return resp.json()[1]
    except: pass
    return []


# --- Парсинг сайта: вытаскиваем тему из Title и H1 ---
def extract_site_info(url):
    print(f"📄 Парсинг контента: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    info = {'topics': set()}
    try:
        if not url.startswith('http'): url = 'https://' + url
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            if soup.title and soup.title.string:
                clean = re.sub(r'[^\w\sа-яА-ЯёЁ]', ' ', soup.title.string)
                info['topics'].add(" ".join(clean.split()[:3]))
            h1 = soup.find('h1')
            if h1:
                info['topics'].add(h1.get_text().strip())
    except Exception as e:
        print(f"⚠️ Ошибка парсинга: {e}")
    return list(info['topics'])


# --- Агрегатор: собираем семантику из всех источников ---
def collect_comprehensive_semantics(base_url):
    all_results = {}

    # Стратегия А: берём ключевые слова по которым уже ранжируется домен
    domain_keywords = get_domain_rankings(base_url)
    if domain_keywords:
        print(f"✅ Найдено {len(domain_keywords)} запросов через анализ домена!")
        for item in domain_keywords:
            all_results[item['keyword']] = item['volume']

    # Стратегия Б: если данных мало — ищем по теме сайта
    if len(all_results) < 50:
        print("📉 Мало данных по домену. Подключаем расширенный поиск...")
        clean_url = base_url.lower().replace('https://', '').replace('www.', '').split('/')[0]
        topic_from_url = clean_url.split('.')[0].replace('-', ' ')
        if len(topic_from_url) < 3: topic_from_url = "купить"

        seeds = [topic_from_url] + extract_site_info(base_url)
        seeds = list(set(seeds))[:3]
        print(f"🌱 Базовые темы: {seeds}")

        for seed in seeds:
            bk_res = get_related_keywords(seed)
            for item in bk_res:
                all_results[item['keyword']] = max(all_results.get(item['keyword'], 0), item['volume'])

            suggestions = get_google_suggestions(seed) + get_youtube_suggestions(seed)
            for sug in suggestions:
                if sug not in all_results:
                    all_results[sug] = random.randint(50, 1000)

            time.sleep(0.3)

    return [{'keyword': k, 'volume': v} for k, v in all_results.items()]


# --- Celery-задачи ---

@shared_task
def log_seo_analysis_to_clickhouse(
    project_id, project_url, task_name, status,
    keywords_count=0, clusters_count=0, duration_ms=0,
    source='celery', error_message='',
):
    """Асинхронный логгер в ClickHouse. Не прерывает основной пайплайн."""
    try:
        ensure_seo_logs_table_exists()
        client = get_clickhouse_client()
        client.execute(
            """
            INSERT INTO seo_analysis_logs
            (
                event_time, project_id, project_url, task_name, status,
                keywords_count, clusters_count, duration_ms, source, error_message
            )
            VALUES
            """,
            [(
                int(time.time()),
                int(project_id),
                str(project_url or ''),
                str(task_name),
                str(status),
                int(keywords_count or 0),
                int(clusters_count or 0),
                int(duration_ms or 0),
                str(source),
                str(error_message or ''),
            )],
        )
        return "ok"
    except Exception as exc:
        print(f"⚠️ ClickHouse logging failed: {exc}")
        return "failed"


@shared_task
def fetch_keywords_for_project(project_id):
    started_at = time.time()
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return "Project not found"

    keywords_data = collect_comprehensive_semantics(project.url)
    if not keywords_data:
        keywords_data = [{'keyword': 'нет данных', 'volume': 0}]

    try:
        db = project.get_shard_db()
        Keyword.objects.using(db).filter(project=project).delete()
        Cluster.objects.using(db).filter(project=project).delete()
        kws = [Keyword(project=project, shard_key=str(project.id), query=i['keyword'][:250], volume=i['volume']) for i in keywords_data]
        Keyword.objects.using(db).bulk_create(kws, ignore_conflicts=True)
        log_seo_analysis_to_clickhouse.delay(
            project_id=project.id, project_url=project.url,
            task_name='fetch_keywords_for_project', status='success',
            keywords_count=len(kws), clusters_count=0,
            duration_ms=int((time.time() - started_at) * 1000), source='celery_worker',
        )
        return f"Saved {len(kws)} keywords"
    except Exception as e:
        log_seo_analysis_to_clickhouse.delay(
            project_id=project.id, project_url=project.url,
            task_name='fetch_keywords_for_project', status='error',
            keywords_count=0, clusters_count=0,
            duration_ms=int((time.time() - started_at) * 1000), source='celery_worker',
            error_message=str(e)[:1000],
        )
        return f"DB Error: {e}"


@shared_task(bind=True)
def cluster_keywords_for_project(self, project_id):
    started_at = time.time()
    try:
        self.update_state(state='PROGRESS', meta={'process': 'Подготовка данных...', 'percent': 5})

        project = Project.objects.get(id=project_id)
        db = project.get_shard_db()
        kws_qs = list(project.keywords.using(db).values('query', 'volume'))
        if not kws_qs:
            return "No keywords"

        keywords = [k['query'] for k in kws_qs]
        vol_map = {k['query']: (k['volume'] or 0) for k in kws_qs}

        self.update_state(state='PROGRESS', meta={'process': 'Загрузка нейросети и анализ смыслов...', 'percent': 20})
        clustered_data = cluster_keywords(keywords)
        self.update_state(state='PROGRESS', meta={'process': 'Сохранение результатов...', 'percent': 80})

        unique_cluster_ids = set(clustered_data.values())
        cluster_queries = {cid: [] for cid in unique_cluster_ids}
        for query, cluster_id in clustered_data.items():
            cluster_queries[cluster_id].append(query)

        Cluster.objects.using(db).filter(project=project).delete()

        cluster_mapping = {}
        for cid in unique_cluster_ids:
            queries_in_cluster = cluster_queries[cid]
            # Название кластера = слово с наибольшей частотностью и наименьшей длиной
            queries_in_cluster.sort(key=lambda q: (-vol_map.get(q, 0), len(q)))
            best_query = queries_in_cluster[0] if queries_in_cluster else f"Кластер {cid + 1}"
            new_cluster = Cluster.objects.using(db).create(
                project=project, shard_key=str(project.id),
                name=best_query.capitalize(), status='draft'
            )
            cluster_mapping[cid] = new_cluster

        for query, cluster_id in clustered_data.items():
            Keyword.objects.using(db).filter(project=project, query=query).update(cluster=cluster_mapping[cluster_id])

        log_seo_analysis_to_clickhouse.delay(
            project_id=project.id, project_url=project.url,
            task_name='cluster_keywords_for_project', status='success',
            keywords_count=len(kws_qs), clusters_count=len(unique_cluster_ids),
            duration_ms=int((time.time() - started_at) * 1000), source='celery_worker',
        )
        return {'process': 'Готово!', 'percent': 100}

    except Exception as e:
        project_url = ''
        try:
            project_url = project.url
        except Exception:
            pass
        log_seo_analysis_to_clickhouse.delay(
            project_id=project_id, project_url=project_url,
            task_name='cluster_keywords_for_project', status='error',
            keywords_count=0, clusters_count=0,
            duration_ms=int((time.time() - started_at) * 1000), source='celery_worker',
            error_message=str(e)[:1000],
        )
        self.update_state(state='FAILURE', meta={'process': f'Ошибка: {str(e)}', 'percent': 0})
        raise e
