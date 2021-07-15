from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from api.user.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=128, min_length=8, write_only=True)
    username = serializers.CharField(max_length=255, required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["id", "username", "password", "email", "is_active", "date"]

    def create(self, validated_data):

        try:
            User.objects.get(email=validated_data["email"])
        except ObjectDoesNotExist:
            return User.objects.create_user(**validated_data)

        raise ValidationError({"user": "A user with this email address already exists."})

