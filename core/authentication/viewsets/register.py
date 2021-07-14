from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from core.authentication.serializers import RegisterSerializer
from core.authentication.models import ActiveSession


class RegisterViewSet(viewsets.ModelViewSet):
    http_method_names = ['post']
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = ActiveSession.for_user(user)
        res = {
            "token": str(token),
        }

        return Response({
            "user": serializer.data,
            "token": res["token"]
        }, status=status.HTTP_201_CREATED)
