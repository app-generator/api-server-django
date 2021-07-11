from core.authentication.models import ActiveSession
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActiveSession
        fields = ['user', 'token', 'date']
