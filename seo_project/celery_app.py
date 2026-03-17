import os
from celery import Celery

# Устанавливаем настройки Django по умолчанию для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seo_project.settings')

app = Celery('seo_project')

# Загружаем конфигурацию из settings.py, используя префикс CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# ВАЖНО: Автоматически находим задачи в файлах tasks.py всех приложений
app.autodiscover_tasks()