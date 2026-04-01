import os
import django

# Override environment variables if running entirely locally (e.g. via PyCharm) outside Docker
if not os.path.exists('/.dockerenv'):
    os.environ['POSTGRES_HOST'] = '127.0.0.1'
    os.environ['POSTGRES_SHARD1_HOST'] = '127.0.0.1'

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seo_project.settings")
    django.setup()

from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from .models import Project, Cluster, Keyword, AuditLog, APIKey, APILog, AIRole

class ModelLogicTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", url="https://example.com")
        
    def test_project_str(self):
        self.assertEqual(str(self.project), "Test Project")
        
    def test_cluster_shard_key_auto(self):
        cluster = Cluster.objects.create(project=self.project, name="Test Cluster")
        self.assertEqual(cluster.shard_key, str(self.project.id))
        self.assertEqual(str(cluster), "Test Cluster (Черновик)")
        
    def test_keyword_shard_key_auto(self):
        cluster = Cluster.objects.create(project=self.project, name="Cluster 1")
        kw = Keyword.objects.create(project=self.project, query="test query", cluster=cluster, volume=100)
        self.assertEqual(kw.shard_key, str(self.project.id))

class ProjectAPITests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="API Project", url="https://api.com")
        
    def test_list_projects(self):
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
    def test_create_project(self):
        data = {'name': 'New Project', 'url': 'https://new.com'}
        response = self.client.post('/api/projects/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 2)

    def test_uncategorize_keyword(self):
        cluster = Cluster.objects.create(project=self.project, name="C1")
        kw = Keyword.objects.create(project=self.project, query="test", cluster=cluster)
        url = f'/api/projects/{self.project.id}/uncategorize_keyword/'
        res = self.client.post(url, {'keyword_id': kw.id}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        kw.refresh_from_db()
        self.assertIsNone(kw.cluster)

    def test_mass_delete(self):
        Keyword.objects.create(project=self.project, query="good", volume=100)
        Keyword.objects.create(project=self.project, query="bad word", volume=5)
        url = f'/api/projects/{self.project.id}/mass_delete/'
        res = self.client.post(url, {'filters': {'min_volume': 10, 'stop_words': ['bad']}}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Keyword.objects.count(), 1)
        self.assertEqual(Keyword.objects.first().query, "good")

    def test_clear_project(self):
        Cluster.objects.create(project=self.project, name="C1")
        Keyword.objects.create(project=self.project, query="kw1")
        url = f'/api/projects/{self.project.id}/clear_project/'
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Cluster.objects.count(), 0)
        self.assertEqual(Keyword.objects.count(), 0)

class ClusterAPITests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test", url="https://t.com")
        self.cluster = Cluster.objects.create(project=self.project, name="C1")
        
    def test_change_status(self):
        url = f'/api/clusters/{self.cluster.id}/change_status/'
        res = self.client.post(url, {'status': 'ready'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.status, 'ready')

    def test_move_keyword(self):
        cluster2 = Cluster.objects.create(project=self.project, name="C2")
        kw = Keyword.objects.create(project=self.project, query="kw", cluster=self.cluster)
        url = f'/api/clusters/{cluster2.id}/move_keyword/'
        res = self.client.post(url, {'keyword_id': kw.id}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        kw.refresh_from_db()
        self.assertEqual(kw.cluster, cluster2)

class UtilityMocksTests(APITestCase):
    @patch('analyzer.views.analyze_serp')
    def test_analyze_competitors(self, mock_analyze):
        mock_analyze.return_value = {'competitors_urls': ['https://a.com']}
        res = self.client.post('/api/projects/analyze_competitors/', {'query': 'test'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('competitors_urls', res.data)
        
    @patch('analyzer.views.check_site_health')
    def test_project_audit(self, mock_health):
        mock_health.return_value = {'score': 90, 'checks': []}
        project = Project.objects.create(name="A", url="https://a.com")
        res = self.client.get(f'/api/projects/{project.id}/audit/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(AuditLog.objects.count(), 1)
