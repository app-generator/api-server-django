# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import template
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.db.models import Max,F,Min,Q,Count,StdDev,Avg, Variance, Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpRequest
from django.shortcuts import render
from django.template import loader
from django.template.loader import render_to_string
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST

from home.models import CVMArquivo, CotacaoIndice, DadosGrafico, Setor, SubSetor, Segmento, Empresa, Acao, Projecao, ProjecaoAcao, Carteira
from home.models import PerfilCarteira, Ranking, Cotacao, CotacaoIndice, Indice,ResultadoAnaliseImportacao,atualizarDadosTesouro,atualizarDadosTreasury, prepararIndicesAnalise, criaInstanciaModelo
from home.models import CVMTabela, CVMCampo, CVMCampoNome, falhasNosAnos, CVMComposicaoCapital, ProfileRanking, ProfileFavorito, Plano
from .forms import FiltroForm, ProfilePlanoForm

from datetime import date, datetime, timedelta, time
from django_htmx.middleware import HtmxDetails
from django_htmx.http import reswap, retarget, trigger_client_event
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh
from django.views.decorators.http import require_POST
import fitz
from fuzzywuzzy import fuzz
import io
import numpy as np
import numbers
import pandas as pd
from pathlib import Path
from pprint import pprint
from render_block import render_block_to_string
import requests
import xml.etree.ElementTree as ET
from yahooquery import Ticker
import zipfile
import warnings

contexto = {}
quantidadeMinimaCotacoes = 30
localArquivos = '/home/pogere/cvm/'
dataDefault = pd.to_datetime('1900-01-01 00:00:00-03',utc=True,infer_datetime_format=True)

# import os
# import os.path
# import ssl
# import stat
# import subprocess
# import sys

# STAT_0o775 = ( stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
#              | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP
#              | stat.S_IROTH |                stat.S_IXOTH )


# def atualizarCertificado():
#     openssl_dir, openssl_cafile = os.path.split(
#         ssl.get_default_verify_paths().openssl_cafile)

#     print(" -- pip install --upgrade certifi")
#     subprocess.check_call([sys.executable,
#         "-E", "-s", "-m", "pip", "install", "--upgrade", "certifi"])

#     import certifi

#     # change working directory to the default SSL directory
#     os.chdir(openssl_dir)
#     relpath_to_certifi_cafile = os.path.relpath(certifi.where())
#     print(" -- removing any existing file or link")
#     try:
#         os.remove(openssl_cafile)
#     except FileNotFoundError:
#         pass
#     print(" -- creating symlink to certifi certificate bundle")
#     os.symlink(relpath_to_certifi_cafile, openssl_cafile)
#     print(" -- setting permissions")
#     os.chmod(openssl_cafile, STAT_0o775)
#     print(" -- update complete")
class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails

def painelAcao(projecaoAcao,user):
    rentabilidade = projecaoAcao.rentabilidade_obtida
    dataInicialCotacoes = projecaoAcao.projecao.data
    qs = projecaoAcao.acao.cotacao_set.filter(data__gte=dataInicialCotacoes).order_by('data').values_list('data','fechamento')
    if len(qs) < quantidadeMinimaCotacoes:
        dataInicialCotacoes = projecaoAcao.projecao.data - timedelta(days=quantidadeMinimaCotacoes- len(qs))
        qs = projecaoAcao.acao.cotacao_set.filter(data__gte=dataInicialCotacoes).order_by('data').values_list('data','fechamento')
    dataUltimaCotacao = qs[len(qs)-1][0]
    df = pd.DataFrame(qs,columns=['data', projecaoAcao.acao.codigo_br])

    # GRAFICO PROJECAO INICIO            
    faixas=pd.DataFrame(
            {'nome': ['Compra','Venda'], 
            'valor_inicial': [projecaoAcao.preco_compra,projecaoAcao.preco_venda], 
            'valor_final': [projecaoAcao.preco_compra * 1.05,projecaoAcao.preco_venda_maximo],
            'posicao': ['bottom','top'],
            'offsetY': [-10,15]})
    graficoProjecao = DadosGrafico(df.set_index('data'),faixas=faixas)  
    # GRAFICO PROJECAO FIM            
            
    # GRAFICO DIVIDENDOS INICIO
    dataInicial = dataUltimaCotacao - timedelta(days=(5 * 365))
    # dataInicial = datetime.utcnow() - timedelta(days=(5 * 365))
    dfDividendos = pd.DataFrame(projecaoAcao.acao.cotacao_set.filter(Q(data__gte=dataInicial) & Q(data__lte=dataUltimaCotacao) & Q(dividendos__gt=0)).order_by('data').values_list('data','dividendos'),columns=['data','dividendos'])
    
    # if len(dfDividendos) > 0:
    #     dfDividendos = dfDividendos.groupby([dfDividendos.data.dt.year,dfDividendos.data.dt.quarter]).sum()
    #     dfDividendos.index.names = ('ano', 'trimestre')
    #     anoPeriodo = [dfDividendos.index.get_level_values('ano').min(),dfDividendos.index.get_level_values('ano').max()]
    #     tam = 1 + anoPeriodo[1] - anoPeriodo[0]
    #     dfn = pd.DataFrame({'1': np.zeros(tam), '2': np.zeros(tam), '3': np.zeros(tam), '4': np.zeros(tam)},index=range(anoPeriodo[0],anoPeriodo[1]+1))
    #     for i in dfDividendos.index: dfn.loc[i[0],str(i[1])] = round(dfDividendos.loc[i[0],i[1]][0],2)
    # else:
    anoPeriodo = [(date.today() - timedelta(days=(5 * 365))).year, date.today().year]
    tam = 1 + anoPeriodo[1] - anoPeriodo[0]
    dfn = pd.DataFrame({'1': np.zeros(tam), '2': np.zeros(tam), '3': np.zeros(tam), '4': np.zeros(tam)},index=range(anoPeriodo[0],anoPeriodo[1]+1))
    if len(dfDividendos) > 0:
        dfDividendos = dfDividendos.groupby([dfDividendos.data.dt.year,dfDividendos.data.dt.quarter]).sum(numeric_only=True)
        dfDividendos.index.names = ('ano', 'trimestre')
        for i in dfDividendos.index: 
            dfn.loc[i[0],str(i[1])] = round(dfDividendos.loc[i[0],i[1]][0],2)

    graficoDividendos = DadosGrafico(dfn,sufixo='º Tri',sobreposto=True)    
    # GRAFICO DIVIDENDOS FIM
    
    # GRAFICO INDICES INICIO
    bova = Acao.objects.get(codigo='BOVA11.SA')
    df1 = pd.DataFrame(bova.cotacao_set.filter(Q(data__gte=dataInicialCotacoes) & Q(data__lte=dataUltimaCotacao)).order_by('data').values_list('data','fechamento'),columns=['data',bova.codigo_br])
    df = df.merge(df1, how='left', left_on='data', right_on='data')
    codigoIndice = ['SELIC','CDI']    
    for i in range(len(codigoIndice)):
        indice = Indice.objects.get(codigo__iexact=codigoIndice[i])
        df1 = pd.DataFrame(indice.cotacaoindice_set.filter(Q(data__gte=dataInicialCotacoes) & Q(data__lte=dataUltimaCotacao)).order_by('data').values_list('data','valor'),columns=['data',codigoIndice[i]])
        df = df.merge(df1, how='left', left_on='data', right_on='data')
    df.fillna(method="ffill", inplace=True)    
    graficoIndices = DadosGrafico(df.set_index('data'), indices=codigoIndice, rentabilidade=rentabilidade)  
    # GRAFICO INDICES FIM
            
    graficoProjecao1 = DadosGrafico(pd.DataFrame({'nome': ['Topo','Base','Obtido'],
                                                  'valor': [projecaoAcao.rentabilidade_maxima,projecaoAcao.rentabilidade,rentabilidade]}).set_index('nome'))
    graficoProjecao2 = DadosGrafico(pd.DataFrame({'nome': ['Transcorrido','Projeção'],
                                                  'valor': [projecaoAcao.dias_transcorridos,projecaoAcao.dias_operacao]}).set_index('nome'))
    favorita = projecaoAcao.acao.profilefavorito_set.filter(profile=user.profile).exists()
    context = {'projecaoAcao':      projecaoAcao,
               'favorita':          favorita,
               'graficoIndices':    graficoIndices,
               'graficoProjecao':   graficoProjecao,
               'graficoProjecao1':  graficoProjecao1,
               'graficoProjecao2':  graficoProjecao2,
               'graficoDividendos': graficoDividendos,
               }
    return context

def subsituiMaiusculaPorUnderline(txt):
    intab = "\/(),.-àáÁãÃâÂàÀéÉêÊíÍóÓôÔõÕúÚçÇ"
    outab = "       aaAaAaAaAeEeEiIoOoOoOuUcC"
    txt = txt.translate(''.maketrans(intab, outab)).lower()
    pro = ['','a','as','e','i','o','os','u','de','da','do','das','dos','para','pelo','por','em','-','no','na','nas','nos','ao','aos','s','com','que','pela']
    ic = ''.join([p.lower().strip(' ')+'_' for p in txt.split() if p not in pro and p.isalnum()])
    ic = ic.replace('__','_').replace(' ','_').removeprefix('_').removesuffix('_')
    return ic

def encontraNomeSimilar(df, nome):
    df['wratio'] = [fuzz.WRatio(nome, rs) for rs in df.nome]
    df['ratio'] = [fuzz.ratio(nome, rs) for rs in df.nome]
    df = df.sort_values('ratio',ascending=False)
    rnome = df.nome.iloc[0] if df.ratio.iloc[0] >= 90 else ''
    df = df.sort_values('wratio',ascending=False)
    wnome = df.nome.iloc[0] if df.wratio.iloc[0] >= 90 else ''
    return rnome if rnome != '' else wnome

def importarEmpresasCVM():
    dadosRename = {'CNPJ_CIA': 'cnpj', 'DENOM_SOCIAL': 'denominacao', 'DENOM_COMERC': 'denom_comerc', 'DT_REG': 'dt_reg', 'DT_CONST': 'dt_const', 'CD_CVM': 'cod_cvm','SIT':'sit','TP_MERC':'tp_merc', 'SETOR_ATIV': 'setor_ativ', 'CATEG_REG': 'categ_reg', 'DT_INI_CATEG': 'dt_ini_categ', 'SIT_EMISSOR': 'sit_emissor', 'DT_INI_SIT_EMISSOR': 'dt_ini_sit_emissor', 'CONTROLE_ACIONARIO': 'controle_acionario', 'TP_ENDER': 'tp_ender', 'LOGRADOURO': 'logradouro', 'COMPL': 'compl', 'BAIRRO': 'bairro', 'MUN': 'mun', 'UF': 'uf', 'PAIS': 'pais', 'CEP': 'cep', 'DDD_TEL': 'ddd_tel', 'TEL': 'tel', 'EMAIL': 'email', 'TP_RESP': 'tp_resp', 'RESP': 'resp', 'DT_INI_RESP': 'dt_ini_resp', 'LOGRADOURO_RESP': 'logradouro_resp', 'COMPL_RESP': 'compl_resp', 'BAIRRO_RESP': 'bairro_resp', 'MUN_RESP': 'mun_resp', 'UF_RESP': 'uf_resp', 'PAIS_RESP': 'pais_resp', 'CEP_RESP': 'cep_resp', 'DDD_TEL_RESP': 'ddd_tel_resp', 'TEL_RESP': 'tel_resp', 'EMAIL_RESP': 'email_resp', 'CNPJ_AUDITOR': 'cnpj_auditor', 'AUDITOR': 'auditor'}
    dadosEssenc = ['CNPJ_CIA','DENOM_SOCIAL','DENOM_COMERC','DT_REG','DT_CONST','SIT','TP_MERC','CD_CVM','SETOR_ATIV','CATEG_REG','DT_INI_CATEG','SIT_EMISSOR','DT_INI_SIT_EMISSOR','CONTROLE_ACIONARIO','TP_ENDER','LOGRADOURO','COMPL','BAIRRO','MUN','UF','PAIS','CEP','DDD_TEL','TEL','EMAIL','TP_RESP','RESP','DT_INI_RESP','LOGRADOURO_RESP','COMPL_RESP','BAIRRO_RESP','MUN_RESP','UF_RESP','PAIS_RESP','CEP_RESP','DDD_TEL_RESP','TEL_RESP','EMAIL_RESP','CNPJ_AUDITOR','AUDITOR']
    dfEmpresas = pd.read_csv('/home/pogere/cvm/cad_cia_aberta.csv',sep=';', encoding = "ISO-8859-1")
    dfEmpresas = dfEmpresas.drop_duplicates('CD_CVM').dropna(subset=['CD_CVM','TP_MERC'])
    # dfEmpresas = dfEmpresas[((~dfEmpresas.TP_MERC.isin(['BOLSA','BALCÃO ORGANIZADO','BALCÃO NÃO ORGANIZADO'])) | (dfEmpresas.SIT.isin(['ATIVO','FASE OPERACIONAL']))) & (dfEmpresas.CD_CVM != 0) & (~dfEmpresas.CONTROLE_ACIONARIO.isin(['PRIVADO']))][dadosEssenc]
    dfEmpresas = dfEmpresas[((~dfEmpresas.TP_MERC.isin(['BOLSA','BALCÃO ORGANIZADO','BALCÃO NÃO ORGANIZADO'])) | (dfEmpresas.SIT.isin(['ATIVO','FASE OPERACIONAL']))) & (dfEmpresas.CD_CVM != 0) & (~dfEmpresas.SIT_EMISSOR.isin(['FALIDA']) & (~dfEmpresas.DENOM_SOCIAL.str.contains('EM LIQUIDAÇÃO',regex=False)))][dadosEssenc]
    dfEmpresas = dfEmpresas.rename(columns=dadosRename)
    dfEmpresas['nome'] = dfEmpresas.denominacao
    dfEmpresas['segmento_id'] = 75
    dfEmpresas['codigo'] = ''
    dfEmpresas['dt_reg'] = pd.to_datetime(dfEmpresas.dt_reg,utc=True,infer_datetime_format=True)
    dfEmpresas['dt_const'] = pd.to_datetime(dfEmpresas.dt_const,utc=True,infer_datetime_format=True)
    dfEmpresas['dt_ini_categ'] = pd.to_datetime(dfEmpresas.dt_ini_categ,utc=True,infer_datetime_format=True)
    dfEmpresas['dt_ini_sit_emissor'] = pd.to_datetime(dfEmpresas.dt_ini_sit_emissor,utc=True,infer_datetime_format=True)
    dfEmpresas['dt_ini_resp'] = pd.to_datetime(dfEmpresas.dt_ini_resp,utc=True,infer_datetime_format=True)
    
    df = pd.DataFrame(Empresa.objects.all().values('nome', 'codigo'))
    instancias = []
    for i, e in dfEmpresas.iterrows():
        emp, incluir = Empresa.objects.filter(Q(cod_cvm=e.cod_cvm)&Q(cnpj=e.cnpj)).first(), True
        if not emp: 
            similar = encontraNomeSimilar(df,e.nome)
            if similar: 
                print(e.nome, e.cnpj, df[df.nome == similar].iloc[0].codigo, similar)
                emp = Empresa.objects.filter(nome=similar).first()
                if emp.cnpj == '' or emp.cnpj == e.cnpj:
                    for c in dfEmpresas.columns: 
                        if c not in ['codigo','segmento_id']: setattr(emp,c,e[c]) 
                    emp.save()
                    incluir = False
                else:
                    dfEmpresas.loc[i,'codigo'] = emp.codigo
            if incluir: instancias.append(Empresa(**criaInstanciaModelo(Empresa,dfEmpresas.loc[i],dfEmpresas.columns)))
    Empresa.objects.bulk_create(instancias)

def importaEstruturaTabelaCVM():
    # campos = ['CNPJ_CIA','DT_REFER','VERSAO','DENOM_CIA','CD_CVM','GRUPO_DFP','MOEDA','ESCALA_MOEDA','ORDEM_EXERC','DT_INI_EXERC','DT_FIM_EXERC','COLUNA_DF','CD_CONTA','DS_CONTA','VL_CONTA','ST_CONTA_FIXA']
    dfEmpCVM = pd.DataFrame(Empresa.objects.filter(cod_cvm__gt=0).values('cod_cvm')).set_index('cod_cvm')
    p = Path(localArquivos)
    for a in list(sorted(p.glob('**/itr*2021.csv'))): 
        df = pd.read_csv(a,sep=';', encoding = "ISO-8859-1")
        df = df.set_index(['CD_CVM']) 
        df = df.loc[df.index.get_level_values(0).intersection(dfEmpCVM.index)].reset_index().rename(columns={'index':'CD_CVM'})
        if not df.empty:
            la = df.iloc[0]
            empresa = Empresa.objects.filter(cod_cvm=la.CD_CVM).first()
            tabela = CVMTabela.objects.filter(nome=la.GRUPO_DFP).first()
            if not tabela: 
                tabela = CVMTabela(nome=la.GRUPO_DFP)
                tabela.save()
            for i,l in df.iterrows():
                if l.CD_CVM != la.CD_CVM: empresa = Empresa.objects.filter(cod_cvm=l.CD_CVM).first()
                niveis = len(l.CD_CONTA.split('.'))
                if niveis <= tabela.niveis: 
                    campo = tabela.cvmcampo_set.filter(codigo=l.CD_CONTA).first()
                    if not campo:
                        campo = CVMCampo(codigo=l.CD_CONTA,nome=l.DS_CONTA,tabela=tabela)
                        campo.save()
                    campoNome = campo.cvmcamponome_set.filter(empresas__id=empresa.id).first()
                    # campoNome = campo.cvmcamponome_set.filter(empresas__empresa_id=empresa.id).first()
                    if campoNome:
                        if campoNome.nome!=l.DS_CONTA: 
                            campoNome.empresas.remove(empresa)
                            if not campoNome.empresas.exists(): campoNome.delete()
                    campoNome = campo.cvmcamponome_set.filter(nome=l.DS_CONTA).first()
                    if not campoNome:
                        campoNome = CVMCampoNome(campo=campo,nome=l.DS_CONTA)
                        campoNome.save()
                    if not campoNome.empresas.filter(id=empresa.id):
                        campoNome.empresas.add(empresa)
                la = l

def analisarEstruturaCVM():
    for t in CVMTabela.objects.all():
        for c in t.cvmcampo_set.all():
            niveis = len(c.codigo.split('.'))
            if niveis > t.niveis and c.campo == '': 
                # qsCN = c.cvmcamponome_set.all()
                print(c.codigo)
                c.delete()
            elif c.campo == '':
                print(f'Na tabela {t.modelo} criar campo {c.codigo} - {c.nome}')
        
def defineNomesCamposTabelasCVM():
    for t in CVMTabela.objects.all():
        ignorados = 0
        utilizados = 0
        for c in t.campocvm_set.all():
            cn = c.campocvmnome_set.annotate(repeticoes=Count('empresas')).order_by('repeticoes')
            niveis = len(c.codigo.split('.'))
            if niveis <= t.niveis: 
                if c.nome != cn.last().nome or c.campo == '':
                    novo = subsituiMaiusculaPorUnderline(cn.last().nome)
                    existe, i = True, 1
                    while existe:
                        existe = len(t.campocvm_set.filter(Q(campo=novo)&~Q(id=c.id))) > 0
                        novo = novo.removesuffix(str(i-1)) + str(i) if existe else novo
                        i += 1
                    c.nome = cn.last().nome
                    c.campo = novo
                    c.save()
                utilizados += 1
            else: ignorados += 1 
        print(f'Tabela: {t.tabela} Ignorados: {ignorados} Utilizados: {utilizados}')

def identificarEmpresasTipoPeriodoInativo():
    anoAnterior = datetime.today().year - 1
    for e in Empresa.objects.filter(cod_cvm__gt=0):
        df3M = pd.DataFrame(e.cvmresultado_set.filter(Q(tipo_periodo='3M')).values('data_fim_exercicio').order_by('data_fim_exercicio')).rename(columns={'data_fim_exercicio':'data'})
        df12M = pd.DataFrame(e.cvmresultado_set.filter(Q(tipo_periodo='12M')).values('data_fim_exercicio').order_by('data_fim_exercicio')).rename(columns={'data_fim_exercicio':'data'})
        if not df12M.empty and not df3M.empty:
            anoInicial = df3M.data.dt.year.min() if df3M.data.dt.year.min() <= df12M.data.dt.year.min() else df12M.data.dt.year.min()
            e.tipo_periodo = '3M' if (falhasNosAnos(anoInicial,df3M) <= falhasNosAnos(anoInicial,df12M)) and ((df3M.data.dt.year.iloc[-1] - 1) >= df12M.data.dt.year.iloc[-1]) else '12M'
        elif df12M.empty and not df3M.empty: e.tipo_periodo = '3M'
        elif df3M.empty and not df12M.empty: e.tipo_periodo = '12M'
        if df12M.empty and df3M.empty: e.ativo = False
        else: e.ativo = df3M.data.dt.year.iloc[-1] >= anoAnterior if e.tipo_periodo == '3M' else df12M.data.dt.year.iloc[-1] >= anoAnterior
        e.save()

def eliminarRegistrosDuplicadosCVM():
    for t in CVMTabela.objects.all():
        for e in Empresa.objects.filter(cod_cvm__gt=0):
            qsm = getattr(e,t.modelo.lower()+'_set').values('data_fim_exercicio','data_referencia').order_by('data_fim_exercicio','-data_referencia').distinct('data_fim_exercicio') 
            for d in qsm:
                qs = getattr(e,t.modelo.lower()+'_set').filter(Q(data_fim_exercicio=d['data_fim_exercicio'])&~Q(data_referencia=d['data_referencia']))
                if len(qs) > 0:
                    print(f"Empresa: {e.id} Fim: {d['data_fim_exercicio']} Ref: {d['data_referencia']}")
                    qs.delete()

def apresentarInformacoesCVM():
    # for t in CVMTabela.objects.all():
    for t in CVMTabela.objects.filter(modelo='CVMBalancoPassivo'):
        for e in Empresa.objects.filter(Q(cod_cvm__gt=0)&Q(codigo='KLBN')):
            r = getattr(e,t.modelo.lower()+'_set').filter(Q(data_fim_exercicio__year=2022)&Q(data_fim_exercicio__month=6)).first()
            print(t.modelo)
            if r:
                for c in t.cvmcampo_set.filter(~Q(campo='')):
                    cn = c.cvmcamponome_set.filter(empresas=e).first()
                    if cn: print(c.codigo,';', cn.nome,';', str(getattr(r,c.campo)).replace('.',','))

def corrigirEmpresas():                
    p = Path(localArquivos)
    a = list(p.glob('empresas-corrigir.csv'))[0]
    df = pd.read_csv(a,sep=',', encoding='UTF-8')
    for i,l in df[df.CVM != 0].iterrows():
        try:
            e = Empresa.objects.get(cod_cvm=l.CVM)
            s = Segmento.objects.filter(nome=l.SEGMENTO)[0]
        except:
            print(f'Erro empresa {l.CVM} - {l.NOME}')
        if e.codigo == '' or l.TICKET == 'NÃO B3' or (e.segmento != s and e.segmento.nome == 'Outros'): 
            e.codigo = l.TICKET if l.TICKET != 'NÃO B3' else ''
            e.segmento = s
            e.tipo_investimento = 'B' if l.TICKET != 'NÃO B3' else 'O'
            e.save()

def eliminarEmpresasNaoBolsa():
    cont = 1
    for e in Empresa.objects.filter(codigo=''):
        print(cont, e.nome)
        e.delete()
        cont += 1

def concatenarDadosAcoesDuplicadas(permanecer, eliminar):
    atualizar = False
    for campo in permanecer._meta.fields:
        conteudo = getattr(permanecer,campo.attname)
        if isinstance(conteudo,numbers.Number) and not campo.is_relation:
            if getattr(eliminar,campo.attname) != 0 and conteudo == 0: 
                setattr(permanecer,campo.attname,getattr(eliminar,campo.attname))
        elif isinstance(conteudo,date):
            if getattr(eliminar,campo.attname) != dataDefault and conteudo == dataDefault:
                setattr(permanecer,campo.attname,getattr(eliminar,campo.attname))
        elif isinstance(conteudo,str):
                if getattr(eliminar,campo.attname) != '' and conteudo == '':
                    setattr(permanecer,campo.attname,getattr(eliminar,campo.attname))
        elif campo.attname == 'segmento_id':
                if getattr(eliminar,campo.attname) != 75 and conteudo == 75:
                    setattr(permanecer,campo.attname,getattr(eliminar,campo.attname))
        atualizar = conteudo != getattr(permanecer,campo.attname) or atualizar
    if atualizar: permanecer.save()
    eliminar.delete()

def eliminarDuplicidadeCodigoAcaoEmpresa():
    relacionamento = ['Acao','CVMCampoNome','CVMBalancoAtivo','CVMBalancoAtivoIndividual','CVMBalancoPassivo','CVMBalancoPassivoIndividual','CVMFluxoCaixaDireto','CVMFluxoCaixaDiretoIndividual','CVMFluxoCaixaIndireto','CVMFluxoCaixaIndiretoIndividual','CVMResultado','CVMResultadoAbrangente','CVMResultadoAbrangenteIndividual','CVMResultadoIndividual','CVMValorAdicionado','CVMValorAdicionadoIndividual']
    codigoDuplicados = Empresa.objects.filter(~Q(codigo='')).values('codigo').annotate(Count('codigo')).filter(codigo__count__gt=1).order_by('codigo')
    for c in codigoDuplicados:
        ed = Empresa.objects.filter(codigo=c['codigo']).order_by('id')
        # for e in ed:
        #     print(e.id,e.codigo, e.nome, e.cod_cvm, e.cnpj, sep=';')
        dicRel, atualizar = {}, False
        for r in relacionamento:
            rels = []
            for i in range(len(ed)):
                if len(getattr(ed[i],r.lower()+'_set').all())>0: rels.append(ed[i].id) 
                # if len(getattr(ed[i],r.lower()+'_set').filter(data_fim_exercicio__year=2022))>0: rels.append(ed[i].id) 
            dicRel[r] = rels if len(rels)>0 else None
        sr = pd.Series(dicRel).dropna()
        print(c['codigo'],sr,sep='\n')
        if 'Acao' in sr.index:
            ids = list(dict.fromkeys([k for i in sr.index[1:] for k in sr[i]]))
            if len(sr.Acao) == 1:
                if len(ids) == 1 and sr.Acao[0] != ids[0]:
                    for a in Acao.objects.filter(empresa_id=sr.Acao[0]):
                        a.empresa_id = ids[0]
                        a.save()
                    atualizar = True
        else: 
            ids = list(dict.fromkeys([k for i in sr.index for k in sr[i]]))
            atualizar = True
        if atualizar:
            print(ids)
            ep = ed.get(id=ids[0])
            for e in ed:
                if e.id != ep.id and (e.cod_cvm == 0 or e.cod_cvm == ep.cod_cvm): 
                    print(f"Substituir empresa {e.id} pela {ep.id} na ação duplicada {c['codigo']}")
                    concatenarDadosAcoesDuplicadas(ep,e)

def ajustarAcoes():
    variacoes = ['3.SA', '4.SA', '5.SA', '6.SA', '11.SA']
    dfe = pd.DataFrame()
    dfe['codigo'] = ''
    dfe['regs'] = 0
    for e in Empresa.objects.filter(~Q(codigo='')):
        for v in variacoes:
            ticket, eliminar = e.codigo + v, False
            tck = Ticker(ticket)            
            df = tck.history(period='1d', interval='1d')
            if len(df) > 0 and type(df) is pd.DataFrame:
                df.reset_index(inplace=True)
                if df.date.iloc[0] > (datetime.today() - timedelta(days=5)).date():
                    try:
                        Acao.objects.get(codigo=ticket)
                    except:
                        print(e.nome, ticket)
                        Acao(empresa=e,codigo=ticket).save()
                else: eliminar = df.date.iloc[0] < (datetime.today() - timedelta(days=120)).date()
            else: eliminar = True
            if eliminar:
                try:
                    acao = Acao.objects.get(codigo=ticket)
                    # print(f'Ação {ticket} deve ser eliminada')
                    dfe = pd.concat([dfe,pd.DataFrame({'codigo': [ticket,],'regs': acao.cotacao_set.aggregate(Count('acao_id'))['acao_id__count'],'ultima': acao.cotacao_set.aggregate(Max('data'))['data__max']})])
                    acao.ativo = False
                    acao.save()
                except:
                    eliminar = False
    dfe = dfe.drop_duplicates().sort_values('codigo')
    print(dfe[:50])
    print(dfe[50:100])
    print(dfe[100:200])

def importarDadosCVM():
    # campos = ['CNPJ_CIA','DT_REFER','VERSAO','DENOM_CIA','CD_CVM','GRUPO_DFP','MOEDA','ESCALA_MOEDA','ORDEM_EXERC','DT_INI_EXERC','DT_FIM_EXERC','COLUNA_DF','CD_CONTA','DS_CONTA','VL_CONTA','ST_CONTA_FIXA']
    p = Path(localArquivos)
    dfEmpCVM = pd.DataFrame(Empresa.objects.filter(cod_cvm__gt=0).values('cod_cvm')).set_index('cod_cvm')
    for a in list(sorted(p.glob('**/itr_cia_aberta_[A-Z]*.csv'))): 
        tipoPeriodo = '3M' if 'itr' in a.name else '12M'
        dm = pd.to_datetime(datetime.fromtimestamp(a.stat().st_mtime).ctime(),utc=True)
        dc = pd.to_datetime(datetime.fromtimestamp(a.stat().st_ctime).ctime(),utc=True)
        print(a, f'Criação: {dc} Modificado: {dm}')
        cvmarquivo = CVMArquivo.objects.filter(nome=a).first()
        importar = cvmarquivo.data_modificado != dm if cvmarquivo else True
        if importar: 
            ordem = ['GRUPO_DFP','DENOM_CIA','CD_CVM','VERSAO','DT_INI_EXERC','DT_FIM_EXERC','MOEDA','ESCALA_MOEDA','DT_REFER']
            comparacaoNovo = ['GRUPO_DFP','CD_CVM','MOEDA','ESCALA_MOEDA','DT_INI_EXERC','DT_FIM_EXERC']
            df = pd.read_csv(a,sep=';', encoding = "ISO-8859-1")
            if not df.empty:
                ordem = [c for c in ordem if c in df.columns] 
                temDataIni = 'DT_INI_EXERC' in df.columns
                comparacaoNovo = list(set(comparacaoNovo) & set(df.columns))
                df.DT_REFER = pd.to_datetime(df.DT_REFER,utc=True,infer_datetime_format=True)
                df['DT_INI_EXERC'] = pd.to_datetime(df.DT_INI_EXERC,utc=True,infer_datetime_format=True) if temDataIni else pd.to_datetime('1900-01-01 00:00:00-03',utc=True,infer_datetime_format=True)
                df.DT_FIM_EXERC = pd.to_datetime(df.DT_FIM_EXERC,utc=True,infer_datetime_format=True)
                tabela = CVMTabela.objects.filter(Q(nome=df.iloc[0].GRUPO_DFP)&Q(importar=True)).first()
                if tabela:
                    if temDataIni:
                        df['INT_EXERC'] = df.DT_FIM_EXERC - df.DT_INI_EXERC
                        if not tabela.acumulado: df = df[((df.INT_EXERC.dt.days > 280)|(df.INT_EXERC.dt.days < 100))&(df.INT_EXERC.dt.days > 75)]
                    df = df.set_index(['CD_CVM','DT_INI_EXERC','DT_FIM_EXERC','MOEDA']) #'DT_REFER',
                    dfDadosGravados = pd.DataFrame(apps.get_model('home', tabela.modelo).objects.all().annotate(cod_cvm=F('empresa__cod_cvm')).values())
                    dfDadosGravados.set_index(['cod_cvm','data_inicio_exercicio','data_fim_exercicio','moeda'],inplace=True) #'data_referencia',
                    df = df.loc[df.index.get_level_values(0).intersection(dfEmpCVM.index)]
                    df = df.loc[df.index.difference(dfDadosGravados.index)].reset_index().sort_values(by=ordem).reset_index(drop=True)
                    if not df.empty:
                        instancias, la, inicio, naLista, existe, atualizar = [], df.iloc[0], True, False, False, False
                        empresa = Empresa.objects.filter(cod_cvm=la.CD_CVM).first()
                        for i,l in df.iterrows():
                            if l.CD_CVM != la.CD_CVM: empresa, inicio = Empresa.objects.filter(cod_cvm=l.CD_CVM).first(), True
                            if not l[comparacaoNovo].compare(la[comparacaoNovo]).empty:
                                if atualizar: 
                                    print(f'Modelo: {tabela.modelo} Empresa: {empresa.denominacao} inicio: {objeto.data_inicio_exercicio.strftime("%d/%m/%Y")} Fim: {objeto.data_fim_exercicio.strftime("%d/%m/%Y")}')
                                    setattr(objeto,'data_referencia',la.DT_REFER)
                                    if not naLista: instancias.append(objeto) if novo else objeto.save()
                                atualizar, inicio, naLista, existe = False, True, False, False
                            if empresa: 
                                if inicio:
                                    if tipoPeriodo == '12M':
                                        objeto = getattr(empresa,tabela.modelo.lower()+'_set').filter(Q(data_fim_exercicio=l.DT_FIM_EXERC)&Q(moeda=l.MOEDA)).first()
                                    else:
                                        objeto = getattr(empresa,tabela.modelo.lower()+'_set').filter(Q(data_inicio_exercicio=l.DT_INI_EXERC)&Q(data_fim_exercicio=l.DT_FIM_EXERC)&Q(moeda=l.MOEDA)).first()
                                    novo, inicio = not objeto, False
                                    if novo:
                                        objeto = next((obj for obj in instancias if obj.empresa.cod_cvm==l.CD_CVM and obj.data_fim_exercicio==l.DT_FIM_EXERC and obj.data_inicio_exercicio==l.DT_INI_EXERC and obj.moeda==l.MOEDA),None)
                                        if not objeto:
                                            objeto = apps.get_model('home', tabela.modelo)(empresa=empresa,data_inicio_exercicio=l.DT_INI_EXERC,data_fim_exercicio=l.DT_FIM_EXERC,data_referencia=l.DT_REFER,ordem_exercicio=l.ORDEM_EXERC,versao=l.VERSAO,moeda=l.MOEDA,escala_moeda=l.ESCALA_MOEDA,tipo_periodo=tipoPeriodo) 
                                        else: naLista = True
                                    existe = (not novo or naLista) and objeto.data_referencia >= l.DT_REFER
                                if not existe:
                                    try: campo = tabela.cvmcampo_set.get(codigo=l.CD_CONTA)
                                    except: campo = False
                                    if campo: 
                                        if campo.campo != '':
                                            atualizar = (getattr(objeto,campo.campo) != l.VL_CONTA and getattr(objeto,'data_referencia') < l.DT_REFER) or novo or atualizar
                                            if atualizar: setattr(objeto,campo.campo,l.VL_CONTA)
                            la = l
                        if atualizar: 
                            print(f'Modelo: {tabela.modelo} Empresa: {empresa.denominacao} inicio: {objeto.data_inicio_exercicio.strftime("%d/%m/%Y")} Fim: {objeto.data_fim_exercicio.strftime("%d/%m/%Y")}')
                            setattr(objeto,'data_referencia',la.DT_REFER)
                            if not naLista: instancias.append(objeto) if novo else objeto.save()
                        apps.get_model('home', tabela.modelo).objects.bulk_create(instancias)

            if cvmarquivo: 
                cvmarquivo.data_modificado = dm
                cvmarquivo.data_criado = dc
            else: cvmarquivo = CVMArquivo(nome=a,data_criado=dc,data_modificado=dm,sucesso=True)
            cvmarquivo.save()
    camposNaoAtualizar = ['versao',]
    for t in CVMTabela.objects.filter(Q(importar=True)):
        for r in apps.get_model('home', t.modelo).objects.filter((Q(data_inicio_exercicio__month=1)|Q(data_inicio_exercicio__month=12))&Q(data_fim_exercicio__month=12)):
            ta = apps.get_model('home', t.modelo).objects.filter(Q(empresa=r.empresa)&Q(data_fim_exercicio__year=r.data_fim_exercicio.year)&~Q(data_fim_exercicio__month=12))
            if len(ta) == 3:
                for c in r._meta.fields:
                    if not (c.is_relation or c.primary_key or c.attname in camposNaoAtualizar) and isinstance(getattr(r,c.attname),numbers.Number):
                        setattr(r,c.attname,getattr(r,c.attname) - getattr(ta[0],c.attname) - getattr(ta[1],c.attname) - getattr(ta[2],c.attname))
                r.data_inicio_exercicio = pd.to_datetime(str(r.data_fim_exercicio.year)+'-10-01 00:00:00-03',utc=True,infer_datetime_format=True)
                # Se houver um registro de quarto trimestre eliminar e salvar o novo
                qs = apps.get_model('home', t.modelo).objects.filter(Q(empresa=r.empresa)&Q(data_fim_exercicio=r.data_fim_exercicio)&Q(data_inicio_exercicio=r.data_inicio_exercicio))
                if qs.exists(): qs.first().delete()
                r.save()
            else:
                print(f'Modelo: {t.modelo} Ano: {r.data_fim_exercicio.year} Empresa: {r.empresa.nome} Trimestres: {len(ta)}')
                if r.data_fim_exercicio.year == 2017:
                    r.delete()

def obterDadosXMLComposicaoCapital(arquivo):
    tree = ET.parse(arquivo)
    root = tree.getroot()
    di = root.find('DadosITR')
    if di is None: di = root.find('DadosDFP')
    dic = {}
    dic['data_referencia'] = pd.to_datetime(di.find('DataReferencia').text,utc=True,infer_datetime_format=True)
    dtIni = di.find('DtInicioTrimestreAtual')
    if dtIni is None: dtIni = di.find('DtInicioUltimoExercicioSocial')
    dic['data_inicio_exercicio'] = pd.to_datetime(dtIni.text,utc=True,infer_datetime_format=True)
    dtFim = di.find('DtFimTrimestreAtual')
    if dtFim is None: dtFim = di.find('DtFimUltimoExercicioSocial')
    dic['data_fim_exercicio'] = pd.to_datetime(dtFim.text,utc=True,infer_datetime_format=True)
    dic['moeda'] = int(di.find('Moeda').text)
    dic['escala_moeda'] = di.find('EscalaMoeda').text
    dic['versao'] = int(di.find('VersaoPlanoContas').text)
    cc = di.find('Formulario').find('DadosEmpresa').find('ComposicaoCapital')
    ci = cc.find('CaptalIntegralizado')
    if ci is None: ci = cc.find('CapitalIntegralizado')
    dic['on_mercado'] = float(ci.find('Ordinarias').text) if ci.find('Ordinarias').text else 0
    dic['pn_mercado'] = float(ci.find('Preferenciais').text) if ci.find('Preferenciais').text else 0
    t = cc.find('Tesouraria')
    dic['on_tesouraria'] = float(t.find('Ordinarias').text) if t.find('Ordinarias').text else 0
    dic['pn_tesouraria'] = float(t.find('Preferenciais').text) if t.find('Preferenciais').text else 0
    df = pd.DataFrame(dic,index=[0,])
    return df

def obterDadosPDFComposicaoCapital(arquivo):
    df = pd.DataFrame()
    doc = fitz.open(arquivo) 
    for pg in doc.pages(1):
        # cc = pg.get_text("Dados da Empresa / Composição do Capital")
        cc = pg.get_text("Número de Ações")
        if cc:
            lista = cc.split('\n')
            dic = {}
            if ('Trimestre Atual' in lista or 'Último Exercício Social' in lista):
                idxtri = lista.index('Trimestre Atual') if 'Trimestre Atual' in lista else lista.index('Último Exercício Social')
                # dic['data_referencia'] = pd.to_datetime(di.find('DataReferencia').text,utc=True,infer_datetime_format=True)
                dic['data_inicio_exercicio'] = pd.to_datetime('1900-01-01 00:00:00-03',utc=True,infer_datetime_format=True)
                dic['data_fim_exercicio'] = pd.to_datetime(lista[idxtri+1],utc=True,infer_datetime_format=True)
                # dic['moeda'] = int(di.find('Moeda').text)
                # dic['escala_moeda'] = di.find('EscalaMoeda').text
                # dic['versao'] = int(di.find('VersaoPlanoContas').text)
                if 'Do Capital Integralizado' in lista:
                    idxon = lista.index('Ordinárias') if 'Ordinárias' in lista else -1
                    idxpn = lista.index('Preferenciais') if 'Preferenciais' in lista else -1
                    dic['on_mercado'] = float(lista[idxon+1].replace('.','')) if idxon != -1 else 0
                    dic['pn_mercado'] = float(lista[idxpn+1].replace('.','')) if idxpn != -1 else 0
                if 'Em Tesouraria' in lista:
                    idxon = lista.index('Ordinárias',idxon+1) if 'Ordinárias' in lista else -1
                    idxpn = lista.index('Preferenciais',idxpn+1) if 'Preferenciais' in lista else -1
                    dic['on_tesouraria'] = float(lista[idxon+1].replace('.','')) if idxon != -1 else 0
                    dic['pn_tesouraria'] = float(lista[idxpn+1].replace('.','')) if idxpn != -1 else 0
                df = pd.DataFrame(dic,index=[0,])
                break
    return df

def importarDadosLinkEmpresasCVM():
    p = Path(localArquivos)
    dfEmpCVM = pd.DataFrame(Empresa.objects.filter(cod_cvm__gt=0).values('cod_cvm','id','nome')).set_index('cod_cvm')
    # dfEmpCVM = pd.DataFrame(Empresa.objects.filter(cod_cvm=10456).values('cod_cvm','id')).set_index('cod_cvm')
    for a in list(sorted(p.glob('**/???_cia_aberta_????.csv'))):
        dm = pd.to_datetime(datetime.fromtimestamp(a.stat().st_mtime).ctime(),utc=True)
        dc = pd.to_datetime(datetime.fromtimestamp(a.stat().st_ctime).ctime(),utc=True)
        print(a, f'Criação: {dc} Modificado: {dm}')
        cvmarquivo = CVMArquivo.objects.filter(Q(nome=a)&Q(data_modificado=dm)).first()
        importar = cvmarquivo.data_modificado != dm if cvmarquivo else True
        erroLink = False
        if importar: 
            try:
                df = pd.read_csv(a,sep=';', encoding = "ISO-8859-1")
                if not df.empty: 
                    df = df.set_index(['CD_CVM']) #'DT_REFER',
                    df = df.loc[df.index.intersection(dfEmpCVM.index)]
                    for COD_CVM,l in df.iterrows():
                        cvmlink = CVMArquivo.objects.filter(nome=l.LINK_DOC)
                        if not cvmlink.exists():
                            try:
                                # r = http.request('GET',l.LINK_DOC)
                                with warnings.catch_warnings():
                                    warnings.simplefilter('ignore')
                                    r = requests.get(l.LINK_DOC, verify=False)
                                z = zipfile.ZipFile(io.BytesIO(r.content))
                                a1 = list(filter(lambda x: (x.endswith('.xml')) & (x.find(str(COD_CVM)) != -1), z.namelist()))
                                if not a1: a1 = list(filter(lambda x: (x.endswith('.pdf')) & (x.find(str(COD_CVM)) != -1), z.namelist()))
                                if a1: 
                                    pf = Path(localArquivos+'/zip/'+a1[0])
                                    if pf.exists(): Path.unlink(pf)
                                    z.extract(a1[0],localArquivos + '/zip')
                                    arquivo = localArquivos+'/zip/'+a1[0]
                                    df = obterDadosXMLComposicaoCapital(arquivo) if '.xml' in a1[0] else obterDadosPDFComposicaoCapital(arquivo)
                                    if not df.empty:
                                        empresa = dfEmpCVM[dfEmpCVM.index == COD_CVM]
                                        df['empresa_id'] = empresa.id.iloc[0]
                                        cc = CVMComposicaoCapital.objects.filter(Q(empresa_id=df.empresa_id.iloc[0])&Q(data_inicio_exercicio=df.data_inicio_exercicio.iloc[0])&Q(data_fim_exercicio=df.data_fim_exercicio.iloc[0]))
                                        if not cc: CVMComposicaoCapital(**criaInstanciaModelo(CVMComposicaoCapital,df.iloc[0],df.columns)).save()
                                        CVMArquivo(nome=l.LINK_DOC,data_criado=dc,data_modificado=dm,sucesso=True).save()
                                        print(f'{empresa.nome.iloc[0]} - {df.data_fim_exercicio.iloc[0]}')
                                    # df1 = pd.read_xml(localArquivos+'/zip/'+a1)
                                    # print(df1)
                            except Exception as inst:
                                print(f'Erro no link {l.LINK_DOC} - {inst}')
                                erroLink = True
                if cvmarquivo and not erroLink: 
                    cvmarquivo.data_modificado = dm
                    cvmarquivo.data_criado = dc
                else: cvmarquivo = CVMArquivo(nome=a,data_criado=dc,data_modificado=dm,sucesso=True)
                cvmarquivo.save()
            except Exception as inst:
                print(f'Erro no arquivo {a} - {inst}')

def criarContexto(usuario, textoPesquisa=''):
    print('Início carga contexto global:',datetime.now())
    global contexto
    if usuario.profile.projecao_tipo == 'u':
        projecoesFiltradas = list(Projecao.objects.all().order_by('-data').values_list('id', flat=True)[:usuario.profile.projecao_ultimas])
    elif usuario.profile.projecao_tipo == 'n':
        projecoesFiltradas = list(Projecao.objects.all().order_by('-data').values_list('id', flat=True)[1:2:])
    else:        
        dtFim = usuario.profile.projecao_periodo_fim + timedelta(hours=24)
        # dtFim = pd.to_datetime(usuario.profile.projecao_periodo_fim,utc=True,infer_datetime_format=True) + timedelta(hours=24)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            projecoesFiltradas = list(Projecao.objects.filter(Q(data__gte=usuario.profile.projecao_periodo_inicio)&Q(data__lte=dtFim)).order_by('-data').values_list('id', flat=True))
    acoes = Acao.objects.all()
    if textoPesquisa:
        empresas = Empresa.objects.annotate(cont=Count('pk', filter=Q(acao__codigo_br__icontains=textoPesquisa))).filter(cont__gt=0)
        setores = Setor.objects.annotate(cont=Count('pk', filter=Q(subsetor__segmento__empresa__acao__codigo_br__icontains=textoPesquisa))).filter(cont__gt=0)
    else:
        empresas = Empresa.objects.all()
        setores = Setor.objects.all()

    perfisCarteiras = PerfilCarteira.objects.all()
    # rankingsFiltrados = Ranking.objects.filter(Q(profileranking__profile=usuario.profile)&Q(profileranking__pranking_visivel=True))
    # rankingsFiltrados = (profileranking__profile=)).annotate('profileranking__pranking_visivel') # &Q(profileranking__pranking_visivel=True))
    
    carteiras = Carteira.objects.all()  
    projecoes = Projecao.objects.get(id=projecoesFiltradas[0]) if len(projecoesFiltradas) == 1 else Projecao.objects.all()
    
    contexto = {'projecoes':         projecoes,
                'projecoesFiltradas':projecoesFiltradas,
                'carteiras':         carteiras,
                'perfisCarteiras':   perfisCarteiras,
                'acoes':             acoes,
                'empresas':          empresas,
                'setores':           setores,
                'rankings':          Ranking.objects.all(),
                # 'rankingsFiltrados': rankingsFiltrados,
                'atualizar':         True,
                'user':              usuario,
                'pesquisar':         textoPesquisa.upper(),
                'cores':            ['bg-c-red','bg-c-red','bg-c-red','bg-c-red','bg-c-purple','bg-c-purple','bg-c-purple','bg-c-yellow','bg-c-yellow','bg-c-yellow','bg-c-blue','bg-c-blue','bg-c-blue','bg-c-green','bg-c-green','bg-c-green']}

    print('Fim carga contexto global:',datetime.now())
    return contexto

class AtualizacaoDadosAcoesView(TemplateView):
    def __init__(self):
        TemplateView.__init__(self)
        # atualizarCertificado()
        # eliminarDuplicidadeCodigoAcaoEmpresa()
        # ajustarAcoes()
        # corrigirEmpresas()
        # eliminarEmpresasNaoBolsa()
        # importarEmpresasCVM()    
        # eliminarRegistrosDuplicadosCVM()
        # apresentarInformacoesCVM()
        # importaEstruturaTabelaCVM()
        # analisarEstruturaCVM()        
        # defineNomesCamposTabelasCVM()

        importarDadosCVM()
        importarDadosLinkEmpresasCVM()
        # identificarEmpresasTipoPeriodoInativo()
        for acao in Acao.objects.filter(ativo=True):
            acao.importarDados()

    template_name = "home/parcial/resultado.html"    

class VerificacaoDadosAcoesView(TemplateView):
    def __init__(self):
        TemplateView.__init__(self)
        ResultadoAnaliseImportacao.objects.all().delete()
        for acao in Acao.objects.all():
        # for acao in Acao.objects.filter(codigo='ITUB3.SA'):
        # for acao in Acao.objects.filter(id=5):
            # acao.verificarDuplicidadeDadosImportados()
            # acao.verificarFaltasDadosImportados()
            print(acao.codigo)
            acao.ajustarLPATrimestre4()

    template_name = "home/parcial/resultado.html"    

class AtualizacaoDadosIndicesView(TemplateView):
    def __init__(self):
        TemplateView.__init__(self)
        for indice in Indice.objects.all():
        # for acao in Acao.objects.filter(codigo='PETR3.SA'):
            indice.importarDados()
        atualizarDadosTesouro()
        # atualizarDadosTreasury()
    
    template_name = "home/parcial/resultado.html"    

class VerificacaoDadosIndicesView(TemplateView):
    def __init__(self):
        TemplateView.__init__(self)
        ResultadoAnaliseImportacao.objects.all().delete()
        for indice in Indice.objects.all():
            indice.verificarDuplicidadeDadosImportados()
            indice.verificarFaltasDadosImportados()
    
    template_name = "home/parcial/resultado.html"    

class AnaliseView(TemplateView):
    def __init__(self):
        TemplateView.__init__(self)
        dt = pd.to_datetime(datetime.today().date(),utc=True,infer_datetime_format=True)
        # p = Projecao.objects.filter(data__week=dt.isocalendar().week)
        p = Projecao.objects.filter(data__month__gte=dt.month-2)
        if not p: 
            p = Projecao(data=dt)
            p.save()
        else: p = p[0]
        p.projetar()

    template_name = "home/parcial/resultado.html"    

class IndexView(TemplateView):
    def __init__(self):
        TemplateView.__init__(self)
    
    template_name = "home/index.html"    

    def get_context_data(self, **kwargs):
        self.contexto = criarContexto(self.request.user)
        md = Projecao.objects.aggregate(Max('data'))['data__max']
        projecaoAcao = self.request.user.profile.projecaoacao if self.request.user.profile.projecaoacao else Projecao.objects.filter(data=md).projecaoacao_set.filter(acao__codigo='ABEV3.SA').first()
        context = super().get_context_data(**kwargs)
        context = {**context,**self.contexto,**painelAcao(projecaoAcao,self.request.user)}
        return context

class TemplateResponsePesquisa(TemplateResponse):    
    
    def render(self) -> SimpleTemplateResponse:
        response = super().render()
        response = reswap(response, "innerHTML")
        response = retarget(response, "#menu-lateral")
        if 'projecaoAcaoPesquisa' in response.context_data:
            response = trigger_client_event(
                response,
                "atualizarPainel",
                {'projecaoAcao': response.context_data['projecaoAcaoPesquisa']},
                after="settle",
            )
        return response
class TemplateResponseSidebar(TemplateResponse):    
    
    def render(self) -> SimpleTemplateResponse:
        response = super().render()
        response = reswap(response, "innerHTML")
        response = retarget(response, "#menu-lateral")
        response = trigger_client_event(
            response,
            "escondeSpinnerFiltro",
            {'alterou_ranking': response.context_data['rank'] if 'rank' in response.context_data else False},
            after="settle",
        )
        return response

class TemplateResponseAssinatura(TemplateResponse):    
    
    def render(self) -> SimpleTemplateResponse:
        response = super().render()
        response = trigger_client_event(
            response,
            'aplicarFiltro',
            {},
            after="settle",
        )
        return response

class TemplateResponseNada(TemplateResponse):    
    
    def render(self) -> SimpleTemplateResponse:
        response = super().render()
        response = reswap(response, "innerHTML")
        response = retarget(response, "#nada")
        response = trigger_client_event(
            response,
            "escondeSpinnerFiltro",
            {'alterou_ranking': False},
            after="settle",
        )
        return response

class TemplateResponseBlock(TemplateResponse):    
    
    def render(self) -> SimpleTemplateResponse:
        simpleTR = super().render()
        simpleTR.content = render_block_to_string(self.template_name,'content',self.context_data)
        return simpleTR

class AplicarFiltro(TemplateView):
    template_name = 'includes/navbar.html'    

    def render_to_response(self, context, **response_kwargs):
        return TemplateResponseSidebar(self.request, self.get_template_names()[0], context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        global contexto
        criarContexto(self.request.user)        
        self.contexto = contexto
        context = {**context,**self.contexto}
        return context    

class ManterFiltro(TemplateView):
    template_name = 'home/parcial/nada.html'    

    def render_to_response(self, context, **response_kwargs):
        return TemplateResponseNada(self.request, self.get_template_names()[0], context)
class Agradecimento(TemplateView):
    template_name = 'home/parcial/agradecimento.html'    

    def render_to_response(self, context, **response_kwargs):
        return TemplateResponseAssinatura(self.request, self.get_template_names()[0], context)

def filtrar(request: HtmxHttpRequest) -> HttpResponse:
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        f = FiltroForm(request.POST, instance=request.user.profile)
        # check whether it's valid:
        if f.is_valid():
            if f.has_changed():
                f.save()
                return HttpResponseRedirect('/aplicar-filtro/' + ('1' if f.alterou_ranking else '0'))
            else:
                return HttpResponseRedirect('/manter-filtro/')

    # if a GET (or any other method) we'll create a blank form
    else:
        f = FiltroForm(instance=request.user.profile)

    return render(request, 'home/parcial/configuracoes.html', {'form': f})

def Assinar(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == 'POST':
        f = ProfilePlanoForm(request.POST, instance=request.user.profile)
        if f.is_valid():
            if f.has_changed():
                f.save()
                return HttpResponseRedirect('/agradecimento/')
            # else:
                # return HttpResponseRedirect('/assinatura/')

    else:
        f = ProfilePlanoForm(instance=request.user.profile)
    return render(request, 'home/parcial/assinatura.html', {'form': f})

class TemplateResponseFavorito(TemplateResponse):    
    
    def render(self) -> SimpleTemplateResponse:
        response = super().render()
        response = retarget(response, "#menu-favorito")
        return response

class Favoritar(TemplateView):
    template_name = 'includes/menu-favorito.html'    

    def render_to_response(self, context, **response_kwargs):
        acao = ProjecaoAcao.objects.get(id=self.kwargs['pk']).acao
        qs = self.request.user.profile.profilefavorito_set.filter(acao=acao)
        if qs.exists(): qs.delete()
        else: ProfileFavorito(profile=self.request.user.profile,acao=acao).save()
        return TemplateResponseFavorito(self.request, self.get_template_names()[0], context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        global contexto
        self.contexto = contexto
        context = {**context,**self.contexto}
        return context    

class Pesquisar(TemplateView):
    template_name = 'includes/navbar.html'    

    def render_to_response(self, context, **response_kwargs):
        if self.template_name == 'home/parcial/nada.html':
            return TemplateResponseNada(self.request, self.get_template_names()[0], context)
        else:
            return TemplateResponsePesquisa(self.request, self.get_template_names()[0], context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if (kwargs['txt'] == '%' and contexto['pesquisar'] == "") or (kwargs['txt'].upper() == contexto['pesquisar']):
            self.template_name = 'home/parcial/nada.html'    
        else:
            self.contexto = criarContexto(self.request.user,'' if kwargs['txt'] == '%' else kwargs['txt'])        
            for projecao in Projecao.objects.all():
                projecaoAcao = projecao.projecaoacao_set.filter(Q(acao__codigo__icontains=kwargs['txt'])|Q(acao__empresa__nome__icontains=kwargs['txt'])).first()
                if projecaoAcao: 
                    context['projecaoAcaoPesquisa'] = projecaoAcao.id
                    break
            context = {**context,**self.contexto}
        return context    
class ProjecaoDetailView(DetailView):
    model = ProjecaoAcao    
    template_name = "home/parcial/painel-projecao.html"    
    
    def __init__(self):
        DetailView.__init__(self)
        global contexto
        self.contexto = contexto
        
    def get_context_data(self, **kwargs):
        self.request.user.profile.projecao_acao_id = self.get_object().id
        self.request.user.save()
        context = super().get_context_data(**kwargs)
        context = {**context,**self.contexto,**painelAcao(self.get_object(),self.request.user)}
        return context            
        
    # def render_to_response(self, context, **response_kwargs):
    #     return TemplateResponseBlock(self.request, self.get_template_names()[0], context)
       
@login_required(login_url="/login/")
def pages(request):
    context = {}
    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    try:

        load_template = request.path.split('/')[-1]

        if load_template == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))
        context['segment'] = load_template

        html_template = loader.get_template('/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))
