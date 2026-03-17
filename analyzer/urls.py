from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, ClusterViewSet, APIKeyViewSet, APILogViewSet, AIRoleViewSet, get_task_status

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'clusters', ClusterViewSet, basename='cluster')
router.register(r'api-keys', APIKeyViewSet, basename='apikey')
router.register(r'api-logs', APILogViewSet, basename='apilog')
router.register(r'ai-roles', AIRoleViewSet, basename='airole')

urlpatterns = [
    path('', include(router.urls)),
    path('task_status/<str:task_id>/', get_task_status, name='task_status'),
]