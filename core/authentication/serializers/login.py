from rest_framework import serializers
from core.user.serializers import UserSerializer


class LoginSerializer(serializers.ModelSerializer, UserSerializer):
    pass
