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
            dados = {
                'pessoal':
                    {'primeiroNome': user.profile.primeiro_nome, 
                     'ultimoNome': user.profile.ultimo_nome, 
                     'celular': user.profile.celular, 
                     'perfil': user.profile.perfil, 
                     'email': user.profile.email, 
                     'endereco': user.profile.endereco },
                'minhaConta':
                    {'nomeUsuario': user.username,
                    'email': user.email},
                'redefinirSenha':
                    {'senhaAtual': user.password}
            }
            # resp = user.check_password('Teste2022')
            # resp = user.check_password('Teste202')
            return Response(dados, status=status.HTTP_200_OK)
        except Exception as exceptionObj:
            return Response({}, status=status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED)

class GravarDadosCadastroViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        try:
            user = User.objects.get(username=request.user)
            user.profile.primeiro_nome = request.data['dados']['primeiroNome']
            user.profile.ultimo_nome = request.data['dados']['ultimoNome']
            user.profile.celular = request.data['dados']['celular']
            user.profile.perfil = request.data['dados']['perfil']
            user.profile.emai = request.data['dados']['email']
            user.profile.endereco = request.data['dados']['endereco']
            user.profile.save()
            return Response({'success': True},status=status.HTTP_200_OK)
        except Exception as exceptionObj:
            return Response({}, status=status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED)
