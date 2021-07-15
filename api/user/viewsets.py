from api.user.serializers import UserSerializer
from api.user.models import User
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import mixins


class UserViewSet(viewsets.GenericViewSet, mixins.UpdateModelMixin):
    serializer_class = UserSerializer
