"""
analyzer/routers.py
-------------------
Абстрактный слой для подготовки к горизонтальному шардированию.

Текущее поведение:
    Всё направляется в базу 'default'. Это безопасно для разработки.

Как использовать несколько шардов (производство):
    1. Добавьте в settings.DATABASES дополнительные БД:
       DATABASES = {
           'default': {...},
           'shard_1': {...},
           'shard_2': {...},
       }
    2. Раскомментируйте логику маршрутизации в ShardRouter._resolve_shard().
    3. Убедитесь, что shard_key проставляется перед save() во всех моделях.

Модели, поддерживающие шардирование:
    - analyzer.Cluster  (shard_key = str(project_id))
    - analyzer.Keyword  (shard_key = str(project_id))
"""


# Список моделей, которые будут участвовать в шардировании
SHARDABLE_MODELS = {'cluster', 'keyword'}

# Соответствие: (shard_key_hash % N) → имя БД
# Заполнять при добавлении реальных шардов
SHARD_MAP = {
    0: 'shard_1',
    # 1: 'shard_2',
}
NUM_SHARDS = len(SHARD_MAP) or 1


class ShardRouter:
    """
    Маршрутизатор БД на основе поля shard_key.

    Текущий режим: pass-through (всё → 'default').
    Для активации шардирования — заполните SHARD_MAP и NUM_SHARDS выше.
    """

    def _resolve_shard(self, hints: dict) -> str | None:
        """
        Определяет имя БД по shard_key из hints.
        hints передаются через Model.objects.using_hint(shard_key='...') (кастомный менеджер)
        или задаются вручную через db_hints при вызове QuerySet.using().

        Возвращает строку — имя базы данных из settings.DATABASES,
        или None, если шардирование не настроено.
        """
        shard_key = hints.get('shard_key')
        if shard_key is not None and SHARD_MAP:
            shard_index = int(shard_key) % NUM_SHARDS
            return SHARD_MAP.get(shard_index, 'default')
        return None

    def db_for_read(self, model, **hints):
        """Маршрутизация READ-запросов."""
        if model._meta.model_name in SHARDABLE_MODELS:
            return self._resolve_shard(hints) or 'default'
        return 'default'

    def db_for_write(self, model, **hints):
        """Маршрутизация WRITE-запросов."""
        if model._meta.model_name in SHARDABLE_MODELS:
            return self._resolve_shard(hints) or 'default'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Разрешаем связи внутри одного шарда.
        При мультишардовой архитектуре FK между шардами недопустимы.
        """
        # Пока используется один default — разрешаем всё
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Миграции выполняются только на 'default'."""
        return db == 'default'
