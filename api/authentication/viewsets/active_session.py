from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated


class ActiveSessionViewSet(viewsets.ModelViewSet):
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        pass
