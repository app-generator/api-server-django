from rest_framework import serializers


from api.authentication.models import ActiveSession
from api.user.serializers import UserSerializer


class ActiveSessionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActiveSession
        fields = ['username', 'token', 'date']
