Активация python:
python3 -m venv venv
source venv/bin/activate

Запустить терминал для Django:
python manage.py runserver

Запустить терминал для Celery:
celery -A seo_project.celery_app:app worker -l info --pool=threads

Запустить терминал для NPM и перейти в seo-frontend(cd seo-frontend):
npm run dev
