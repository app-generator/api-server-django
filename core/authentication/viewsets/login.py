from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from core.authentication.serializers import LoginSerializer


class LoginViewSet(viewsets.ModelViewSet):
    http_method_names = ['post']
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
