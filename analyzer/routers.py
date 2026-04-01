
# Список моделей, которые будут участвовать в шардировании
SHARDABLE_MODELS = {'cluster', 'keyword'}

# Соответствие: (shard_key_hash % N) → имя БД
SHARD_MAP = {
    0: 'default',
    1: 'shard_1',
}
NUM_SHARDS = len(SHARD_MAP)


class ShardRouter:
    def _resolve_shard(self, hints: dict) -> str | None:
        shard_key = hints.get('shard_key')
        if not shard_key:
            instance = hints.get('instance')
            if hasattr(instance, '_meta') and instance._meta.model_name == 'project':
                shard_key = str(instance.id)
            elif instance and hasattr(instance, 'shard_key') and instance.shard_key:
                shard_key = instance.shard_key

        if shard_key is not None and SHARD_MAP:
            try:
                shard_index = int(shard_key) % NUM_SHARDS
                return SHARD_MAP.get(shard_index, 'default')
            except ValueError:
                shard_index = abs(hash(shard_key)) % NUM_SHARDS
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
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'analyzer':
            return True # Разрешаем везде для отладки
        return db == 'default'
