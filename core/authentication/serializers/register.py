from rest_framework import serializers
from core.user.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=128, min_length=8, write_only=True)
    username = serializers.CharField(max_length=255, read_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "is_active", "date"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
