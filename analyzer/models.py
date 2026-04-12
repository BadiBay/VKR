from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVectorField


class Project(models.Model):
    name = models.CharField(max_length=200)
    url = models.URLField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_shard_db(self):
        try:
            return 'shard_1' if int(self.id) % 2 == 1 else 'default'
        except (ValueError, TypeError):
            return 'default'


class Cluster(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('ready', 'Готов к генерации'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="clusters", db_constraint=False)
    name = models.CharField(max_length=255, default="Новый кластер")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    # Ключ шардирования — заполняется автоматически из project_id
    shard_key = models.CharField(max_length=64, db_index=True)

    def save(self, *args, **kwargs):
        if self.project_id and not self.shard_key:
            self.shard_key = str(self.project_id)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    class Meta:
        indexes = [
            models.Index(fields=['project', 'status'], name='cluster_project_status_idx'),
            models.Index(fields=['shard_key', 'project'], name='cluster_shard_project_idx'),
        ]


class Keyword(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="keywords", db_constraint=False)
    query = models.CharField(max_length=255)
    volume = models.IntegerField(null=True, blank=True)
    cluster = models.ForeignKey(Cluster, on_delete=models.SET_NULL, null=True, blank=True, related_name="keywords")

    # Ключ шардирования — заполняется автоматически из project_id
    shard_key = models.CharField(max_length=64, db_index=True)

    # Поле tsvector для полнотекстового поиска — заполняется триггером в миграции
    search_vector = SearchVectorField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.project_id and not self.shard_key:
            self.shard_key = str(self.project_id)
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('project', 'query')
        indexes = [
            GinIndex(fields=['search_vector'], name='keyword_search_vector_gin_idx'),
            models.Index(fields=['cluster', 'project'], name='keyword_cluster_project_idx'),
            models.Index(fields=['shard_key', 'cluster'], name='keyword_shard_cluster_idx'),
        ]


class AuditLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="audits")
    score = models.IntegerField(default=0)
    checks_json = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audit {self.project.name} - Score: {self.score}"

    class Meta:
        managed = False  # Таблицей управляет PostgreSQL через миграцию
        db_table = 'analyzer_auditlog'
        indexes = [
            models.Index(fields=['created_at'], name='auditlog_created_at_idx'),
            models.Index(fields=['project', 'created_at'], name='auditlog_project_date_idx'),
        ]


class APIKey(models.Model):
    name = models.CharField(max_length=255)
    key = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class APILog(models.Model):
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    endpoint = models.CharField(max_length=255)
    tokens_used = models.IntegerField(default=0)
    status = models.CharField(max_length=50)
    duration_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_at'], name='apilog_created_at_idx'),
            models.Index(fields=['endpoint', 'status'], name='apilog_endpoint_status_idx'),
        ]


class AIRole(models.Model):
    name = models.CharField(max_length=255)
    prompt_addition = models.TextField()

    def __str__(self):
        return self.name