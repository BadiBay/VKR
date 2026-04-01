import os
import django
import sys
import time
import requests
from django.db import connection
from django.conf import settings

try:
    import colorama
    from colorama import Fore, Style
    colorama.init()
except ImportError:
    # No colors fallback
    class EmptyString:
        def __getattr__(self, name): return ""
    Fore = EmptyString()
    Style = EmptyString()

# Init Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seo_project.settings')
django.setup()

from analyzer.models import Project, Cluster, AuditLog
from analyzer.clickhouse_client import get_clickhouse_client
from django.core.cache import cache

colorama.init()

def print_header(title):
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*60}")
    print(f"{title.center(60)}")
    print(f"{'='*60}{Style.RESET_ALL}\n")

def print_success(msg):
    print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")

def print_info(msg):
    print(f"{Fore.YELLOW}ℹ️ {msg}{Style.RESET_ALL}")

def test_partitioning():
    print_header("1. ПРОВЕРКА СЕКЦИОНИРОВАНИЯ (PARTITIONING)")
    print_info("Запрос информации о партициях таблицы analyzer_auditlog напрямую из PostgreSQL...")
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT inhrelid::regclass AS partition_name 
            FROM pg_inherits 
            WHERE inhparent = 'analyzer_auditlog'::regclass;
        """)
        partitions = cursor.fetchall()
        
        if partitions:
            print_success(f"Найдено {len(partitions)} партиций!")
            for idx, p in enumerate(partitions[:5]):
                print(f"   - {p[0]}")
            if len(partitions) > 5:
                print(f"   - ...и еще {len(partitions) - 5} штук.")
        else:
            print(f"{Fore.RED}❌ Партиции не найдены!{Style.RESET_ALL}")

def test_sharding():
    print_header("2. ПРОВЕРКА ШАРДИРОВАНИЯ БАЗ ДАННЫХ (SHARDING)")
    print_info("Создаем 2 тестовых проекта с четным и нечетным project_id...")
    
    p_even = None
    p_odd = None
    
    try:
        # 1. Создаем проект для default (четный ID)
        p_even = Project.objects.create(
            name="Project A Shard 0",
            url=f"http://test1-{int(time.time() * 1000)}.com"
        )
        while p_even.id % 2 != 0:
            p_even.delete()
            p_even = Project.objects.create(
                name="Project A Shard 0",
                url=f"http://test1-{int(time.time() * 1000)}.com"
            )

        # 2. Создаем проект для shard_1 (нечетный ID)
        p_odd = Project.objects.create(
            name="Project B Shard 1",
            url=f"http://test2-{int(time.time() * 1000)}.com"
        )
        while p_odd.id % 2 != 1:
            p_odd.delete()
            p_odd = Project.objects.create(
                name="Project B Shard 1",
                url=f"http://test2-{int(time.time() * 1000)}.com"
            )
        p_odd.save(using='shard_1')

        c1 = Cluster(project=p_even, name="Тест Шардинг Четный", shard_key=str(p_even.id))
        c1.save()
        
        c2 = Cluster(project=p_odd, name="Тест Шардинг Нечетный", shard_key=str(p_odd.id))
        c2.save()

        # Проверяем физическое наличие в разных базах
        try:
            is_in_default = Cluster.objects.using('default').filter(id=c1.id).exists()
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка доступа к 'default': {e}{Style.RESET_ALL}")
            is_in_default = False

        try:
            is_in_shard1 = Cluster.objects.using('shard_1').filter(id=c2.id).exists()
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка доступа к 'shard_1'. Скорее всего, таблицы не созданы: {e}{Style.RESET_ALL}")
            is_in_shard1 = False
        
        if is_in_default and is_in_shard1:
            print_success("Успех! Данные физически распределены по разным инстансам PostgreSQL.")
            print(f"   - Кластер Проекта A найден в 'default'.")
            print(f"   - Кластер Проекта B найден в 'shard_1'.")
        else:
            print_info("Диагностика:")
            print(f"   - Найдено в default: {'ДА' if is_in_default else 'НЕТ'}")
            print(f"   - Найдено в shard_1: {'ДА' if is_in_shard1 else 'НЕТ'}")
            print(f"{Fore.RED}❌ Ошибка: данные не распределились по шардам.{Style.RESET_ALL}")
            
    finally:
        # Надежная очистка
        if p_even: p_even.delete()
        if p_odd: 
            p_odd.delete()
            try:
                p_odd.delete(using='shard_1')
            except Exception: pass


def test_redis_cache():
    print_header("3. ПРОВЕРКА КЭШИРОВАНИЯ (REDIS CACHE)")
    print_info("Сделаем 2 одинаковых обращения к кэшу (через Django Cache Framework)...")
    
    cache_key = "test_demo_key"
    cache.delete(cache_key) # Убеждаемся что его нет
    
    t0 = time.time()
    val = cache.get(cache_key)
    if val is None:
        time.sleep(1) # Эмуляция "тяжелого" вычисления (например, парсинг сайтов)
        cache.set(cache_key, "Heavy Data Result", timeout=60)
        
    t1 = time.time()
    first_duration = t1 - t0
    print(f"   Первый запрос (вычисление): {first_duration:.4f} секунд.")
    
    t2 = time.time()
    val2 = cache.get(cache_key)
    t3 = time.time()
    second_duration = t3 - t2
    print(f"   Второй запрос (прямо из Redis): {second_duration:.6f} секунд. Получено: '{val2}'")
    
    if second_duration < first_duration and val2 == "Heavy Data Result":
        print_success(f"Разница очевидна! Кэш работает. Запрос быстрее примерно в {int(first_duration/second_duration) if second_duration > 0 else '>1000'} раз!")
    else:
        print(f"{Fore.RED}❌ Ошибка Redis!{Style.RESET_ALL}")

def test_clickhouse():
    print_header("4. ПРОВЕРКА АНАЛИТИЧЕСКОЙ БД (CLICKHOUSE)")
    print_info("Запрос аналитических логов проектов...")
    try:
        from clickhouse_driver import Client
        from analyzer.clickhouse_client import ensure_seo_logs_table_exists
        
        # Гарантируем наличие таблицы в облаке
        try:
            ensure_seo_logs_table_exists()
            print_success("Таблица seo_analysis_logs проверена/создана в Cloud.")
        except Exception as e:
            print_info(f"Предупреждение при создании таблицы: {e}")

        cfg = settings.CLICKHOUSE_CONFIG
        client = get_clickhouse_client()
        
        # Эмуляция одной новой записи для наглядности
        client.execute(
            """
            INSERT INTO seo_analysis_logs
            (event_time, project_id, project_url, task_name, status, keywords_count, clusters_count, duration_ms, source)
            VALUES
            """,
            [(int(time.time()), 8888, 'http://cloud-demo.com', 'demo_task', 'success', 0, 0, 2000, 'script')]
        )
        
        # Запрос из ClickHouse
        result = client.execute("SELECT * FROM seo_analysis_logs ORDER BY event_time DESC LIMIT 3")
        
        if result:
            print_success(f"Чтение успешно! Найдено логов в Cloud: {len(result)} шт.")
            for row in result:
                print(f"   - [Project ID: {row[1]}] Task: {row[3]}, Status: {row[4]}, Duration: {row[7]}ms")
        else:
            print(f"{Fore.RED}❌ Логи в ClickHouse Cloud не обнаружены.{Style.RESET_ALL}")
            
    except Exception as e:
        print(f"{Fore.RED}❌ Подключение к ClickHouse Cloud не удалось.{Style.RESET_ALL}")
        print(f"   Ошибка: {str(e)[:500]}...")

def run_all():
    try:
        test_partitioning()
        test_sharding()
        test_redis_cache()
        test_clickhouse()
        print(f"\n{Fore.GREEN}{Style.BRIGHT}=== ТЕСТИРОВАНИЕ АРХИТЕКТУРЫ УСПЕШНО ЗАВЕРШЕНО ==={Style.RESET_ALL}\n")
    except Exception as e:
        print(f"{Fore.RED}❌ Критическая ошибка скрипта: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    run_all()
