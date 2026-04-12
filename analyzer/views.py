from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from celery.result import AsyncResult
import time
import urllib.parse
from urllib.parse import unquote
import pandas as pd

from .models import Project, Keyword, Cluster, AuditLog, APIKey, APILog, AIRole
from .serializers import (ProjectSerializer, ProjectDetailSerializer,
                          ClusterSerializer, AuditLogSerializer,
                          APIKeySerializer, APILogSerializer, AIRoleSerializer)
from .tasks import fetch_keywords_for_project, cluster_keywords_for_project

from .services.audit import AuditService
from .services.parsing import ParsingService
from .services.generation import GenerationService
from .services.export import ExportService


# Логируем каждый вызов API в таблицу APILog
def log_api_call(request, endpoint, duration, status_msg, tokens=0):
    ip = request.META.get('REMOTE_ADDR')
    APILog.objects.create(user_ip=ip, endpoint=endpoint, duration_ms=duration, status=status_msg, tokens_used=tokens)


class ClusterViewSet(viewsets.ModelViewSet):
    queryset = Cluster.objects.all()
    serializer_class = ClusterSerializer

    def get_object(self):
        # Ищем кластер по всем шардам
        pk = self.kwargs.get('pk')
        for db in ['default', 'shard_1']:
            try:
                return Cluster.objects.using(db).get(pk=pk)
            except Cluster.DoesNotExist:
                continue
        from django.http import Http404
        raise Http404

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        cluster = self.get_object()
        new_status = request.data.get('status')
        if new_status in dict(Cluster.STATUS_CHOICES):
            cluster.status = new_status
            cluster.save()
            return Response({'status': cluster.status})
        return Response({'error': 'Invalid status'}, status=400)

    @action(detail=True, methods=['post'])
    def move_keyword(self, request, pk=None):
        cluster = self.get_object()
        keyword_id = request.data.get('keyword_id')
        try:
            db = cluster.project.get_shard_db()
            kw = Keyword.objects.using(db).get(id=keyword_id)
            kw.cluster = cluster
            kw.save()
            return Response({'status': 'Keyword moved'})
        except Keyword.DoesNotExist:
            return Response({'error': 'Keyword not found'}, status=404)


class APIKeyViewSet(viewsets.ModelViewSet):
    queryset = APIKey.objects.all()
    serializer_class = APIKeySerializer


class APILogViewSet(viewsets.ModelViewSet):
    queryset = APILog.objects.all().order_by('-created_at')
    serializer_class = APILogSerializer


class AIRoleViewSet(viewsets.ModelViewSet):
    queryset = AIRole.objects.all()
    serializer_class = AIRoleSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve': return ProjectDetailSerializer
        return ProjectSerializer

    @method_decorator(cache_page(60 * 15))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()
        cache.clear()

    @action(detail=True, methods=['post'])
    def uncategorize_keyword(self, request, pk=None):
        project = self.get_object()
        keyword_id = request.data.get('keyword_id')
        try:
            kw = project.keywords.get(id=keyword_id)
            kw.cluster = None
            kw.save()
            return Response({'status': 'Keyword uncategorized'})
        except Keyword.DoesNotExist:
            return Response({'error': 'Keyword not found'}, status=404)

    @action(detail=True, methods=['post'])
    def import_keywords(self, request, pk=None):
        project = self.get_object()
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided'}, status=400)

        try:
            if file_obj.name.endswith('.csv'):
                df = pd.read_csv(file_obj)
            else:
                df = pd.read_excel(file_obj)

            # Пытаемся найти колонку с ключевыми словами и частотностью
            query_col = next((c for c in df.columns if 'query' in c.lower() or 'keyword' in c.lower() or 'слово' in c.lower() or 'фраза' in c.lower()), None)
            vol_col = next((c for c in df.columns if 'vol' in c.lower() or 'частот' in c.lower() or 'ws' in c.lower()), None)

            if not query_col:
                return Response({'error': 'Could not find keyword column'}, status=400)

            keywords = df[query_col].dropna().astype(str).tolist()
            volumes = df[vol_col].fillna(0).astype(int).tolist() if vol_col else [0] * len(keywords)

            db = project.get_shard_db()
            if Keyword.objects.using(db).filter(project=project).count() + len(keywords) > 15000:
                return Response({'error': 'Limit of 15000 keywords per project exceeded'}, status=400)

            kws = []
            for q, v in zip(keywords, volumes):
                q = q.strip()[:250]
                if q: kws.append(Keyword(project=project, shard_key=str(project.id), query=q, volume=v))

            Keyword.objects.using(db).bulk_create(kws, ignore_conflicts=True)
            return Response({'status': f'Imported {len(kws)} keywords'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def mass_delete(self, request, pk=None):
        project = self.get_object()
        filters = request.data.get('filters', {})
        min_volume = filters.get('min_volume')
        stop_words = filters.get('stop_words', [])

        db = project.get_shard_db()
        qs = project.keywords.using(db).all()
        deleted = 0

        if min_volume is not None:
            res = qs.filter(volume__lt=int(min_volume)).delete()
            deleted += res[0]

        if stop_words:
            for word in stop_words:
                res = qs.filter(query__icontains=word).delete()
                deleted += res[0]

        return Response({'status': f'Deleted {deleted} keywords'})

    @action(detail=True, methods=['post'], url_path='reset_clusters')
    def reset_clusters(self, request, pk=None):
        project = self.get_object()
        db = project.get_shard_db()
        only_drafts = request.data.get('only_drafts', False)
        if only_drafts:
            Cluster.objects.using(db).filter(project=project, status='draft').delete()
            return Response({'status': 'Удалены только черновики кластеров'})
        else:
            Cluster.objects.using(db).filter(project=project).delete()
            return Response({'status': 'Все кластеры удалены'})

    @action(detail=True, methods=['post'], url_path='clear_project')
    def clear_project(self, request, pk=None):
        project = self.get_object()
        db = project.get_shard_db()
        Keyword.objects.using(db).filter(project=project).delete()
        Cluster.objects.using(db).filter(project=project).delete()
        return Response({'status': 'Проект очищен от слов и кластеров'})

    @action(detail=True, methods=['post'])
    def run_fetch(self, request, pk=None):
        task = fetch_keywords_for_project.delay(self.get_object().id)
        return Response({'task_id': task.id})

    @action(detail=True, methods=['post'])
    def run_clustering(self, request, pk=None):
        task = cluster_keywords_for_project.delay(self.get_object().id)
        return Response({'task_id': task.id})

    @action(detail=False, methods=['post'])
    def analyze_competitors(self, request):
        query = request.data.get('query', '')
        if not query: return Response({'error': 'No query'}, status=400)

        # Проверяем кэш перед тяжёлым запросом
        cache_key = f"competitors_analysis_{query}"
        cached_data = cache.get(cache_key)
        if cached_data:
            print(f"📦 Возврат из кэша для: {query}")
            return Response(cached_data)

        result = ParsingService.analyze_serp(query)
        cache.set(cache_key, result, timeout=60 * 60)
        return Response(result)

    @action(detail=True, methods=['get'])
    def audit(self, request, pk=None):
        project = self.get_object()
        if not project.url: return Response({'error': 'No URL'}, status=400)

        result = AuditService.check_site_health(project.url)
        AuditLog.objects.create(project=project, score=result['score'], checks_json=result['checks'])
        return Response(result)

    @action(detail=True, methods=['post'])
    def check_position(self, request, pk=None):
        project = self.get_object()
        query = request.data.get('query')
        if not query or not project.url: return Response({'error': 'No data'}, status=400)

        target_domain = project.url.lower().replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
        urls = ParsingService.search_engine_parser(query, limit=50)

        position, found_url = -1, ""
        for i, url in enumerate(urls):
            if target_domain in unquote(url.lower()):
                position, found_url = i + 1, url
                break
        return Response({'position': str(position) if position > 0 else "> 50", 'found_url': found_url})

    @action(detail=True, methods=['post'])
    def download_docx(self, request, pk=None):
        project = self.get_object()
        cluster_id = request.data.get('cluster_id')
        doc_type = request.data.get('doc_type', 'tz')
        text_content = request.data.get('content', '')
        meta_content = request.data.get('meta', '')
        lsi_content = request.data.get('lsi', '')

        if not cluster_id: return Response({'error': 'No cluster_id'}, status=400)

        try:
            db = project.get_shard_db()
            cluster = Cluster.objects.using(db).get(id=cluster_id)
        except Cluster.DoesNotExist:
            return Response({'error': 'Cluster empty or not found'}, status=404)

        main_keyword = cluster.keywords.first().query if cluster.keywords.exists() else 'Без названия'
        cluster_name = main_keyword.capitalize()

        buffer = ExportService.build_docx(
            cluster_name=cluster_name,
            doc_type=doc_type,
            text_content=text_content,
            meta_content=meta_content,
            lsi_content=lsi_content,
        )

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        prefix = "Article" if doc_type == 'article' else "TZ"
        filename = f"{prefix}_{cluster_name}.docx"
        response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{urllib.parse.quote(filename)}'
        return response

    @action(detail=True, methods=['post'])
    def generate_content(self, request, pk=None):
        project = self.get_object()
        cluster_id = request.data.get('cluster_id')
        role_id = request.data.get('role_id')
        custom_lsi = request.data.get('custom_lsi', '')

        if not cluster_id: return Response({'error': 'No cluster_id'}, status=400)

        try:
            db = project.get_shard_db()
            cluster = Cluster.objects.using(db).get(id=cluster_id)
        except Cluster.DoesNotExist:
            return Response({'error': 'Empty or Missing Cluster'}, status=404)

        keywords = cluster.keywords.all().order_by('-volume')
        if not keywords.exists(): return Response({'error': 'Empty keywords'}, status=404)

        main_keyword = keywords.first().query
        cluster_name = main_keyword.capitalize()
        top_keys = [k.query for k in keywords[:5]]
        if custom_lsi: top_keys.extend([x.strip() for x in custom_lsi.split(',')])

        role_prompt = "Ты ведущий эксперт и редактор."
        if role_id:
            try:
                role = AIRole.objects.get(id=role_id)
                role_prompt = role.prompt_addition
            except AIRole.DoesNotExist:
                pass

        t0 = time.time()
        try:
            content = GenerationService.generate_content(
                cluster_name=cluster_name,
                top_keys=top_keys,
                role_prompt=role_prompt,
            )
            duration = int((time.time() - t0) * 1000)
            log_api_call(request, "gigachat_content", duration, "200 OK", 500)
            return Response({'content': content})
        except Exception as e:
            log_api_call(request, "gigachat_content", 0, f"Error: {str(e)[:40]}", 0)
            return Response({'content': f"Ошибка генерации: {str(e)}"}, status=500)

    @action(detail=True, methods=['post'])
    def generate_meta(self, request, pk=None):
        main_keyword = request.data.get('keyword')
        role_id = request.data.get('role_id')
        role_prompt = "Ты SEO-специалист."
        if role_id:
            try:
                role = AIRole.objects.get(id=role_id)
                role_prompt = f"Действуй как {role.name}. {role.prompt_addition}"
            except:
                pass

        t0 = time.time()
        try:
            content = GenerationService.generate_meta(
                main_keyword=main_keyword,
                role_prompt=role_prompt,
            )
            duration = int((time.time() - t0) * 1000)
            log_api_call(request, "gigachat_meta", duration, "200 OK", 100)
            return Response({'content': content})
        except Exception as e:
            log_api_call(request, "gigachat_meta", 0, f"Error: {str(e)[:40]}", 0)
            return Response({'content': f"Ошибка: {e}"}, status=500)


def get_task_status(request, task_id):
    task_result = AsyncResult(task_id)
    response = {'state': task_result.state, 'process': 'Обработка...', 'percent': 0}
    if task_result.state == 'PROGRESS': response.update(task_result.info)
    elif task_result.state == 'SUCCESS': response.update({'process': 'Готово!', 'percent': 100})
    elif task_result.state == 'FAILURE': response.update({'process': 'Ошибка', 'percent': 0})
    return JsonResponse(response)
