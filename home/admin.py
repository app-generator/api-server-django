# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin

# Register your models here.
from home.models import Projecao, ProjecaoAcao, Setor, SubSetor, Segmento, Empresa, Acao, Carteira, PerfilCarteira, Ranking
from api.user.models import User

admin.site.register([User, Setor, SubSetor, Segmento, Empresa, Acao, Projecao, ProjecaoAcao, Carteira, PerfilCarteira, Ranking])
