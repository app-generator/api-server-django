from django.utils.safestring import mark_safe
from django.template import Library
from cmath import isnan, nan

import json

register = Library()

@register.filter(is_safe=True)
def js(obj):
    return mark_safe(json.dumps(obj, indent=4, sort_keys=True, default=str))
    # return mark_safe(json.dumps(obj))

@register.filter
def na_projecao(objetos, projecao):
    return objetos.filter(projecao_acao__projecao=projecao)

@register.filter
def projecaoacao_na_projecao(objetos, projecao):
    qs = objetos.filter(projecao=projecao)
    return qs.first() if qs.exists() else False

@register.filter
def projecaoacao_em_projecoes(objetos, projecoes):
    qs = objetos.filter(projecao_id__in=projecoes)
    return qs.first() if qs.exists() else False

@register.filter
def rankeados_ranking_projecao(objetos, projecao):
    return len(objetos.rankeamento_set.filter(projecao_acao__projecao_id=projecao.id))    

@register.filter
def rank_no_ranking(objetos, ranking):
    obj = objetos.filter(ranking__nome=ranking)
    indice_rank = obj[0].indice_rank if obj else 0
    return indice_rank

@register.filter
def nota_no_ranking(objetos, ranking):
    obj = objetos.filter(ranking__nome=ranking)
    nota = obj[0].nota if obj else ''
    return nota

@register.filter
def ajuda_do_ranking(objetos, ranking):
    obj = objetos.filter(nome=ranking)
    ajuda = obj[0].ajuda if obj else ''
    return ajuda

@register.filter
def index(indexable, i):
    return indexable[int(round(i,0))] if not isnan(i) else 0

@register.filter
def update_variable(value):
    ultima = value
    return ultima

@register.filter
def empresa_na_pesquisa(empresa,pesquisa):
    return empresa.acao_set.filter(codigo_br__icontains=pesquisa).exists()

@register.filter
def segmento_na_pesquisa(segmento,pesquisa):
    return segmento.empresa_set.filter(acao__codigo_br__icontains=pesquisa).exists()

@register.filter
def subsetor_na_pesquisa(subsetor,pesquisa):
    return subsetor.segmento_set.filter(empresa__acao__codigo_br__icontains=pesquisa).exists()

@register.filter
def projecao_no_filtro(projecao,projecaoFiltrada):
    return projecao.id in projecaoFiltrada
