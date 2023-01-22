from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Max,F,Min,Q,Count,StdDev,Avg, Variance, Sum

from api.user.models import User
from api.authentication.models import ActiveSession
from home.models import MenuItem, Profile, ProfileFavorito, ProfileRanking, Acao, Empresa, Projecao, Setor, SubSetor, Segmento
import json
from datetime import date, datetime, timedelta, time
import warnings


class ObterDadosCadastroViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        try:
            user = User.objects.get(username=request.user)
            dados = {'primeiroNome': user.profile.primeiro_nome, 
                     'ultimoNome': user.profile.ultimo_nome, 
                     'telefone': user.profile.telefone, 
                     'perfil': user.profile.perfil, 
                     'email': user.profile.email, 
                     'endereco': user.profile.endereco }
            return Response(dados, status=status.HTTP_200_OK)
        except Exception as exceptionObj:
            return Response({}, status=status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED)
