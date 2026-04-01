from clickhouse_driver import Client
from django.conf import settings


def get_clickhouse_client() -> Client:
    cfg = settings.CLICKHOUSE_CONFIG
    return Client(
        host=cfg['HOST'],
        port=cfg['PORT'],
        user=cfg['USER'],
        password=cfg['PASSWORD'],
        database=cfg['DATABASE'],
        secure=cfg.get('SECURE', False),
    )


def ensure_seo_logs_table_exists() -> None:
    client = get_clickhouse_client()
    client.execute(
        """
        CREATE TABLE IF NOT EXISTS seo_analysis_logs
        (
            event_time DateTime,
            project_id UInt64,
            project_url String,
            task_name LowCardinality(String),
            status LowCardinality(String),
            keywords_count UInt32,
            clusters_count UInt32,
            duration_ms UInt32,
            source LowCardinality(String),
            error_message String
        )
        ENGINE = MergeTree
        ORDER BY (project_id, event_time)
        PARTITION BY toYYYYMM(event_time)
        """
    )
