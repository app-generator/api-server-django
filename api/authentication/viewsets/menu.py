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

icone = {
    'acao': 0,
    'projecao': 1,
    'empresa': 2,
    'setor': 3,
    'subsetor': 3,
    'segmento': 3,
    'ranking': 4,
    'favorito': 5
}

def incluirAcoesMenu(a, prefixo_id, pf):
    prefixo_id += '_' 
    if a.qt_proj == 1:
        i = {'id': prefixo_id + str(a.id), 'title': a.codigo_br, 'type': 'item', 'url': '/', 'icon': icone['acao'], 'breadcrumbs': True}
    else:
        i = {'id': prefixo_id + str(a.id), 'title': a.codigo_br, 'type': 'collapse', 'icon': icone['acao'], 'breadcrumbs': True}     
        i['children'] = [{'id': i['id'] + '_' + str(p.id), 'title': p.projecao.data.strftime("%d %b, %Y"), 'type': 'item', 'url': '/', 'icon': icone['projecao'], 'breadcrumbs': True} for p in a.projecaoacao_set.filter(projecao_id__in=pf).order_by('-projecao__data')]
    return i

def incluirEmpresaMenu(e, prefixo_id, pf):
    prefixo_id += '_' 
    i = {'id': prefixo_id + str(e.id), 'title': e.nome, 'type': 'collapse', 'icon': None, 'breadcrumbs': icone['empresa'], 'children': []}     
    for a in e.acao_set.filter(projecaoacao__projecao_id__in=pf).annotate(qt_proj=Count('projecaoacao__projecao_id')).order_by('codigo_br'):
        i['children'].append(incluirAcoesMenu(a, i['id'], pf))
    return i

def adicionarSubItens(usuario, menu ,item):
    # SELECIONAR PROJEÇÕES PERMITIDAS AO USUÁRIO
    if usuario.profile.projecao_tipo == 'u':
        pf = list(Projecao.objects.all().order_by('-data').values_list('id', flat=True)[:usuario.profile.projecao_ultimas])
    elif usuario.profile.projecao_tipo == 'n':
        pf = list(Projecao.objects.all().order_by('-data').values_list('id', flat=True)[1:2:])
    else:        
        dtFim = usuario.profile.projecao_periodo_fim + timedelta(hours=24)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            pf = list(Projecao.objects.filter(Q(data__gte=usuario.profile.projecao_periodo_inicio)&Q(data__lte=dtFim)).order_by('-data').values_list('id', flat=True))
    # INCLUIR ITENS NO MENU
    item['children'] = []
    if menu == 'menu_acao':
        for a in Acao.objects.filter(projecaoacao__projecao_id__in=pf).annotate(qt_proj=Count('projecaoacao__projecao_id')).order_by('codigo_br'):
            item['children'].append(incluirAcoesMenu(a,'ma', pf))
    if menu == 'menu_empresa':
        for e in Empresa.objects.filter(acao__projecaoacao__projecao_id__in=pf).annotate(Count('id')).order_by('nome'):
            item['children'].append(incluirEmpresaMenu(e,'me',pf))
    if menu == 'menu_setor':
        for s in Setor.objects.filter(subsetor__segmento__empresa__acao__projecaoacao__projecao_id__in=pf).annotate(Count('subsetor__segmento__empresa__acao__projecaoacao__projecao_id')).order_by('nome'):
            i = {'id': 'ms_' + str(s.id), 'title': s.nome, 'type': 'collapse', 'icon': icone['setor'], 'breadcrumbs': True, 'children': []}     
            for ss in s.subsetor_set.filter(segmento__empresa__acao__projecaoacao__projecao_id__in=pf).annotate(qt_proj=Count('segmento__empresa__acao__projecaoacao__projecao_id')).order_by('nome'):
                i1 = {'id': i['id'] + '_' + str(ss.id), 'title': ss.nome, 'type': 'collapse', 'icon': icone['subsetor'], 'breadcrumbs': True, 'children': []}     
                for seg in ss.segmento_set.filter(empresa__acao__projecaoacao__projecao_id__in=pf).annotate(qt_proj=Count('empresa__acao__projecaoacao__projecao_id')).order_by('nome'):
                    i2 = {'id': i1['id'] + '_' + str(seg.id), 'title': seg.nome, 'type': 'collapse', 'icon': icone['segmento'], 'breadcrumbs': True, 'children': []}     
                    for e in seg.empresa_set.filter(acao__projecaoacao__projecao_id__in=pf).annotate(Count('acao__projecaoacao__projecao_id')).order_by('nome'):
                        i2['children'].append(incluirEmpresaMenu(e,i2['id'],pf))
                    i1['children'].append(i2)
                i['children'].append(i1)
            item['children'].append(i)
    if menu == 'menu_projecao':
        for p in Projecao.objects.filter(id__in=pf).annotate(qt_proj=Count('projecaoacao')).filter(qt_proj__gt=0).order_by('-data'):
            i = {'id': 'mp_' + str(p.id), 'title': p.data.strftime("%d %b, %Y"), 'type': 'collapse', 'icon': icone['projecao'], 'breadcrumbs': True}     
            i['children'] = [{'id': i['id'] + '_' + str(pa.id), 'title': pa.acao.codigo_br, 'type': 'item', 'url': 'projecao/'+ str(pa.id), 'icon': icone['acao'], 'breadcrumbs': True} for pa in p.projecaoacao_set.order_by('acao__codigo_br')]
            if len(i['children']): item['children'].append(i)
    if menu == 'menu_ranking':            
        for r in usuario.profile.profileranking_set.filter(pranking_visivel=True).order_by('ranking__ordem'):
            i = {'id': 'mr_' + str(r.id), 'title': r.ranking.nome, 'type': 'collapse', 'icon': icone['ranking'], 'breadcrumbs': True, 'caption': r.ranking.ajuda}     
            qs_p = Projecao.objects.filter(Q(id__in=pf)&Q(projecaoacao__rankeamento__ranking=r.ranking)).annotate(qt_rank=Count('projecaoacao__rankeamento')).filter(qt_rank__gt=0).order_by('-data')
            for p in qs_p:
                prefixo_id = i['id'] + '_' + str(p.id) if len(qs_p) > 1 else i['id']
                a = [{'id': prefixo_id + '_' + str(rnk.projecaoacao.acao.id), 'title': rnk.projecaoacao.acao.codigo_br, 'type': 'item', 'url': 'projecao/'+ str(rnk.projecaoacao.id), 'icon': icone['acao'], 'breadcrumbs': True} for rnk in r.ranking.rankeamento_set.filter(projecaoacao__projecao=p).order_by('-indice_rank')[:usuario.profile.ranking_rankeados]]
                if len(a):
                    if len(qs_p) > 1: i['children'].append({'id': i['id'] + '_' + str(p.projecao.id), 'title': p.projecao.data.strftime("%d %b, %Y"), 'type': 'collapse', 'icon': icone['projecao'], 'breadcrumbs': True, 'children': a}) 
                    else: i['children'] = a
                    item['children'].append(i)
        if not usuario.profile.menu_esconder_inativos:
            for r in usuario.profile.profileranking_set.filter(pranking_visivel=False).order_by('ranking__ordem'):
                i = {'id': 'mr_' + str(r.id), 'title': r.ranking.nome, 'type': 'item', 'url': '/', 'icon': icone['ranking'], 'breadcrumbs': True, 'caption': r.ranking.ajuda, 'disabled': True}     
                item['children'].append(i)
    if menu == 'menu_favorito':            
        for a in Acao.objects.filter(id__in=usuario.profile.profilefavorito_set.values_list('acao_id')).filter(projecaoacao__projecao_id__in=pf).annotate(qt_proj=Count('projecaoacao__projecao_id')).order_by('codigo_br'):
            item['children'].append(incluirAcoesMenu(a,'mf', pf))
    return item

class MenuViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        try:
            excluir = ['pai_id','nome_configuracao','ordem']
            user = User.objects.get(username=request.user)
            menu = []
            for i in MenuItem.objects.filter(type='group'):
                grupo = {c.attname: getattr(i, c.attname) for c in i._meta.fields if getattr(i, c.attname) and c.attname not in excluir}
                grupo['children'] = []
                for i1 in MenuItem.objects.filter(pai_id=i.id):                    
                    item = {c.attname: getattr(i1, c.attname) for c in i1._meta.fields if getattr(i1, c.attname) and c.attname not in excluir}
                    item['icon'] = icone[item['id']]
                    if i1.nome_configuracao: 
                        item['disabled'] = not getattr(user.profile, i1.nome_configuracao)
                        if item['disabled']: 
                            item['type'] = 'item'
                            item['url'] = '/'
                        if not user.profile.menu_esconder_inativos or not item['disabled']:
                            if not item['disabled']: 
                                item = adicionarSubItens(user,i1.nome_configuracao, item)
                            grupo['children'].append(item) 
                    else:
                        grupo['children'].append(item) 
                if len(grupo['children']) > 0: menu.append(grupo) 
            # resp = [
            #             {
            #                 'id': 'investimentos',
            #                 'title': "Investimentos",
            #                 'type': 'group',
            #                 'children': [
            #                     {
            #                         'id': 'acoes',
            #                         'title': 'Ações',
            #                         'type': 'item',
            #                         'url': '/dashboard/default',
            #                         'icon': None,
            #                         'breadcrumbs': True
            #                     },
            #                     {
            #                         'id': 'empresas',
            #                         'title': 'Empresas',
            #                         'type': 'item',
            #                         'url': '/dashboard/analytics',
            #                         'icon': None,
            #                         'breadcrumbs': True
            #                     },
            #                     {
            #                         'id': 'setores',
            #                         'title': 'Setores',
            #                         'type': 'item',
            #                         'url': '/dashboard/analytics',
            #                         'icon': None,
            #                         'breadcrumbs': True
            #                     }
            #                 ]
            #             },
            #             {
            #                 'id': 'analises',
            #                 'title': "Análises",
            #                 'type': 'group',
            #                 'children': [
            #                     {
            #                         'id': 'projecoes',
            #                         'title': 'Projeções',
            #                         'type': 'collapse',
            #                         'icon': None,
            #                         'breadcrumbs': True,
            #                         'disabled': False
            #                     },
            #                     {
            #                         'id': 'rankings',
            #                         'title': 'Rankings',
            #                         'type': 'item',
            #                         'url': '/dashboard/analytics',
            #                         'icon': None,
            #                         'breadcrumbs': True
            #                     },
            #                 ]
            #             }
            # ]
            return Response(menu, status=status.HTTP_200_OK)
        except Exception as exceptionObj:
            return Response({}, status=status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED)
