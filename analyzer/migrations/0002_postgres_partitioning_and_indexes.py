"""
analyzer/migrations/0002_postgres_partitioning_and_indexes.py
--------------------------------------------------------------
Кастомная миграция для PostgreSQL-специфичных функций:

1. Включение расширения pg_trgm (для GIN-индекса по подстрокам).
2. Пересоздание таблицы analyzer_auditlog как PARTITIONED BY RANGE (created_at).
3. Создание ежемесячных секций на 12 месяцев вперёд.
4. Создание функции + триггера автоматического создания новых секций.
5. Добавление поля search_vector + GIN-индекса + триггера для Keyword.

ВНИМАНИЕ: Эта миграция предполагает ЧИСТУЮ БД (без данных в auditlog).
Если данные уже есть — нужна отдельная процедура переноса данных.
"""

from django.db import migrations


# ---- SQL: Extensions -------------------------------------------------------

ENABLE_PG_TRGM = "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# ---- SQL: AuditLog Partitioned Table ---------------------------------------

# Удаляем таблицу, созданную стандартной Django-миграцией,
# и пересоздаём как секционированную.
DROP_AUDITLOG = "DROP TABLE IF EXISTS analyzer_auditlog CASCADE;"

CREATE_AUDITLOG_PARTITIONED = """
CREATE TABLE analyzer_auditlog (
    id          BIGSERIAL,
    project_id  INTEGER NOT NULL
                    REFERENCES analyzer_project(id)
                    ON DELETE CASCADE
                    DEFERRABLE INITIALLY DEFERRED,
    score       INTEGER NOT NULL DEFAULT 0,
    checks_json JSONB   NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)           -- PK должен включать ключ секционирования
) PARTITION BY RANGE (created_at);
"""

# Создание индекса на родительской таблице (наследуется секциями)
CREATE_AUDITLOG_IDX_DATE = """
CREATE INDEX auditlog_created_at_idx
    ON analyzer_auditlog (created_at);
"""

CREATE_AUDITLOG_IDX_PROJECT_DATE = """
CREATE INDEX auditlog_project_date_idx
    ON analyzer_auditlog (project_id, created_at);
"""

# ---- SQL: Auto-create partitions for current year + next 12 months ---------

CREATE_PARTITIONS_FUNCTION = """
CREATE OR REPLACE FUNCTION create_auditlog_partition(target_month DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_date     DATE;
    end_date       DATE;
BEGIN
    start_date     := DATE_TRUNC('month', target_month);
    end_date       := start_date + INTERVAL '1 month';
    partition_name := 'analyzer_auditlog_' || TO_CHAR(start_date, 'YYYY_MM');

    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN   pg_namespace n ON n.oid = c.relnamespace
        WHERE  c.relname = partition_name
          AND  n.nspname = current_schema()
    ) THEN
        EXECUTE FORMAT(
            'CREATE TABLE %I PARTITION OF analyzer_auditlog
             FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
        RAISE NOTICE 'Created partition: %', partition_name;
    END IF;
END;
$$ LANGUAGE plpgsql;
"""

# Создаём секции: текущий месяц + 12 месяцев вперёд
CREATE_INITIAL_PARTITIONS = """
DO $$
DECLARE
    i INTEGER;
BEGIN
    FOR i IN 0..12 LOOP
        PERFORM create_auditlog_partition(
            (DATE_TRUNC('month', NOW()) + (i || ' months')::INTERVAL)::DATE
        );
    END LOOP;
END;
$$;
"""

# Триггерная функция: автоматически создаёт секцию при вставке
CREATE_AUTO_PARTITION_TRIGGER_FN = """
CREATE OR REPLACE FUNCTION auditlog_auto_partition_trigger()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM create_auditlog_partition(NEW.created_at::DATE);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# NOTE: Триггер BEFORE INSERT на родительскую таблицу
CREATE_AUTO_PARTITION_TRIGGER = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE  tgname = 'auditlog_auto_partition'
    ) THEN
        CREATE TRIGGER auditlog_auto_partition
            BEFORE INSERT ON analyzer_auditlog
            FOR EACH ROW EXECUTE FUNCTION auditlog_auto_partition_trigger();
    END IF;
END;
$$;
"""

# ---- SQL: Keyword search_vector GIN -----------------------------------------

ADD_SEARCH_VECTOR_COLUMN = """
ALTER TABLE analyzer_keyword
    ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;
"""

CREATE_KEYWORD_GIN_INDEX = """
CREATE INDEX IF NOT EXISTS keyword_search_vector_gin_idx
    ON analyzer_keyword USING GIN (search_vector);
"""

# Триггер: автом. обновление search_vector при INSERT/UPDATE
CREATE_KEYWORD_TSVECTOR_FN = """
CREATE OR REPLACE FUNCTION keyword_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := TO_TSVECTOR('russian', COALESCE(NEW.query, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_KEYWORD_TSVECTOR_TRIGGER = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE  tgname = 'keyword_search_vector_trigger'
    ) THEN
        CREATE TRIGGER keyword_search_vector_trigger
            BEFORE INSERT OR UPDATE ON analyzer_keyword
            FOR EACH ROW EXECUTE FUNCTION keyword_search_vector_update();
    END IF;
END;
$$;
"""

# ---- Reverse (rollback) SQL --------------------------------------------------

REVERSE_PARTITIONING = """
-- Удаляем секционированную таблицу и пересоздаём простую
DROP TABLE IF EXISTS analyzer_auditlog CASCADE;

CREATE TABLE analyzer_auditlog (
    id          BIGSERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES analyzer_project(id) ON DELETE CASCADE,
    score       INTEGER NOT NULL DEFAULT 0,
    checks_json JSONB   NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

REVERSE_SEARCH_VECTOR = """
DROP TRIGGER  IF EXISTS keyword_search_vector_trigger ON analyzer_keyword;
DROP FUNCTION IF EXISTS keyword_search_vector_update();
ALTER TABLE analyzer_keyword DROP COLUMN IF EXISTS search_vector;
DROP INDEX    IF EXISTS keyword_search_vector_gin_idx;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('analyzer', '0001_initial'),
    ]

    operations = [
        # 1. Расширение pg_trgm (необходимо для GIN по тексту)
        migrations.RunSQL(
            sql=ENABLE_PG_TRGM,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # 2. Пересоздание AuditLog как PARTITIONED TABLE
        migrations.RunSQL(
            sql=DROP_AUDITLOG + CREATE_AUDITLOG_PARTITIONED
                + CREATE_AUDITLOG_IDX_DATE + CREATE_AUDITLOG_IDX_PROJECT_DATE,
            reverse_sql=REVERSE_PARTITIONING,
        ),

        # 3. Функция создания секций + начальные 13 секций (текущий + 12 мес.)
        migrations.RunSQL(
            sql=CREATE_PARTITIONS_FUNCTION + CREATE_INITIAL_PARTITIONS,
            reverse_sql="DROP FUNCTION IF EXISTS create_auditlog_partition(DATE);",
        ),

        # 4. Триггер авто-создания секций
        migrations.RunSQL(
            sql=CREATE_AUTO_PARTITION_TRIGGER_FN + CREATE_AUTO_PARTITION_TRIGGER,
            reverse_sql=(
                "DROP TRIGGER  IF EXISTS auditlog_auto_partition ON analyzer_auditlog;\n"
                "DROP FUNCTION IF EXISTS auditlog_auto_partition_trigger();"
            ),
        ),

        # 5. search_vector + GIN-индекс + триггер для Keyword
        migrations.RunSQL(
            sql=(ADD_SEARCH_VECTOR_COLUMN + CREATE_KEYWORD_GIN_INDEX
                 + CREATE_KEYWORD_TSVECTOR_FN + CREATE_KEYWORD_TSVECTOR_TRIGGER),
            reverse_sql=REVERSE_SEARCH_VECTOR,
        ),
    ]
