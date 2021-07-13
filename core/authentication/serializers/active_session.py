from rest_framework import serializers


from core.authentication.models import ActiveSession
from core.user.serializers import UserSerializer


class ActiveSessionSerializer(serializers.ModelSerializer, UserSerializer):

    class Meta:
        model = ActiveSession
        fields = ['username', 'token', 'date']
