# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.home import views
from apps.home.views import IndexView, ProjecaoDetailView, AtualizacaoDadosAcoesView, VerificacaoDadosAcoesView, Favoritar
from apps.home.views import AtualizacaoDadosIndicesView, VerificacaoDadosIndicesView,AnaliseView,filtrar, AplicarFiltro, ManterFiltro
from apps.home.views import Pesquisar, Assinar, Agradecimento
from django.contrib.auth.decorators import login_required, permission_required
from . import views

# app_name = 'home'
urlpatterns = [
    path('', login_required(IndexView.as_view()), name='home'),
    path('projecao/<int:pk>/', login_required(ProjecaoDetailView.as_view()), name='projecao'),
    path('favorito/<str:pk>/', login_required(Favoritar.as_view()), name='favorito'),
    path('pesquisar/<str:txt>/', login_required(Pesquisar.as_view()), name='pesquisar'),
    path('atualizacao-acao/', login_required(AtualizacaoDadosAcoesView.as_view()), name='atualizacao-acao'),
    path('verificacao-acao/', login_required(VerificacaoDadosAcoesView.as_view()), name='verificacao-acao'),
    path('atualizacao-indice/', login_required(AtualizacaoDadosIndicesView.as_view()), name='atualizacao-indice'),
    path('verificacao-indice/', login_required(VerificacaoDadosIndicesView.as_view()), name='verificacao-indice'),
    path('analise/', login_required(AnaliseView.as_view()), name='analise'),
    path('filtrar/', login_required(filtrar), name='filtrar'),
    path('assinatura/', login_required(Assinar), name='assinatura'),
    path('agradecimento/', login_required(Agradecimento.as_view()), name='agradecimento'),
    path('aplicar-filtro/<int:rank>', login_required(AplicarFiltro.as_view()), name='aplicar-filtro'),
    path('manter-filtro/', login_required(ManterFiltro.as_view()), name='manter-filtro'),

    # Matches any html file
    re_path(r'^.*\.*', views.pages, name='pages'),
]

