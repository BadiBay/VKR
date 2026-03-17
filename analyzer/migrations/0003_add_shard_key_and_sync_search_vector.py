"""
analyzer/migrations/0003_add_shard_key_and_sync_search_vector.py
-----------------------------------------------------------------
Добавляет поля, объявленные в models.py, но отсутствующие в схеме БД:

  • Cluster.shard_key   — реальный ALTER TABLE (новый столбец)
  • Keyword.shard_key   — реальный ALTER TABLE (новый столбец)
  • Keyword.search_vector — SeparateDatabaseAndState:
        столбец уже был создан SQL-миграцией 0002 (ALTER TABLE ... ADD COLUMN),
        поэтому здесь только синхронизируем Django-состояние без повторного DDL.
"""

from django.contrib.postgres.search import SearchVectorField
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analyzer', '0002_postgres_partitioning_and_indexes'),
    ]

    operations = [
        # ------------------------------------------------------------------
        # 1. Cluster.shard_key — новый столбец
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name='cluster',
            name='shard_key',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Ключ шарда (например, str(project_id)). Используется для маршрутизации запросов.',
                max_length=64,
            ),
            preserve_default=False,
        ),

        # ------------------------------------------------------------------
        # 2. Keyword.shard_key — новый столбец
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name='keyword',
            name='shard_key',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Ключ шарда (например, str(project_id)). Используется для маршрутизации запросов.',
                max_length=64,
            ),
            preserve_default=False,
        ),

        # ------------------------------------------------------------------
        # 3. Keyword.search_vector — столбец уже создан в 0002 через SQL.
        #    SeparateDatabaseAndState: только обновляем Django-state,
        #    никакого DDL в БД не выполняется.
        # ------------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[],   # ← пустой: столбец уже есть в БД
            state_operations=[
                migrations.AddField(
                    model_name='keyword',
                    name='search_vector',
                    field=SearchVectorField(blank=True, null=True),
                ),
            ],
        ),
    ]
