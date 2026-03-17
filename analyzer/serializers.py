from rest_framework import serializers
from .models import Project, Keyword, Cluster, AuditLog, APIKey, APILog, AIRole

class KeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Keyword
        fields = ['id', 'query', 'volume', 'cluster']

class ClusterSerializer(serializers.ModelSerializer):
    keywords = KeywordSerializer(many=True, read_only=True)
    class Meta:
        model = Cluster
        fields = ['id', 'name', 'status', 'created_at', 'keywords']

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'url', 'created_at']

class ProjectDetailSerializer(serializers.ModelSerializer):
    keywords = KeywordSerializer(many=True, read_only=True)
    clusters = ClusterSerializer(many=True, read_only=True)
    class Meta:
        model = Project
        fields = ['id', 'name', 'url', 'created_at', 'keywords', 'clusters']

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = '__all__'

class APILogSerializer(serializers.ModelSerializer):
    class Meta:
        model = APILog
        fields = '__all__'

class AIRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRole
        fields = '__all__'