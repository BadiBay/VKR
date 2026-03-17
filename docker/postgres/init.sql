-- Этот скрипт выполняется Postgres при первом создании контейнера.
-- Включаем необходимые расширения.

-- pg_trgm: необходим для GIN-индексов по подстрокам (LIKE '%...%')
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- unaccent: нормализация текста (опционально, полезно для поиска)
CREATE EXTENSION IF NOT EXISTS unaccent;
