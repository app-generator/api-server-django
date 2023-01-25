# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from ast import Delete
from cmath import isnan, nan
from email.policy import default
from optparse import Values
from pyexpat import model
from statistics import mean
from django.db import models
# from django.contrib.auth.models import User
from api.user.models import User
from django.db.models import Max,F,Min,Q,Count,StdDev,Avg, Variance, Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from datetime import date, datetime, timedelta, time
import pandas as pd
from pandas.api.types import CategoricalDtype
import functools as ft
import numpy as np
from yahooquery import Ticker
from bcb import sgs
from feature_engine.creation import CyclicalTransformer
import sklearn.datasets
import sklearn.metrics
import autosklearn.regression
from googletrans import Translator
import urllib
from investpy import bonds
from joblib import dump, load
from random import randint
from fuzzywuzzy import fuzz
# from sqlalchemy import create_engine, false, null, text, true

# Create your models here.

diasSemana = 5
semanasAno = 52
diasMes = int(semanasAno*diasSemana/12)
diasAno = semanasAno*diasSemana
periodosIndicadores = (diasAno*6, diasAno*3, diasAno, diasMes*9, diasMes*6, diasMes*3, diasMes, diasSemana*2, diasSemana)
diasAnalise = diasAno*15*2
diasPrevisao = diasSemana * 5
diasMediaDiferenca = int(diasPrevisao / 2)
quantidadeMinimaTrimestres = 5
quantidadeMinimaAnos = 3
quantidadeMaximaAnos = 10
anoInicial = 2004
diasAcrescimoDadosFundamentos = 40
mediaVolumeMinimo = 10000
diasMediaVolumeMinimo = 60
anoAnterior = datetime.today().year - 1

def subsituiMaiusculaPorUnderline(txt):
    ic = ''.join([p.lower()+'_' for p in txt.rsplit(' ')])
    if ic[0] == '_': ic = ic[1::]
    if ic[len(ic)-1] == '_': ic = ic[:-1:]
    intab = " -áÁãÃâÂàÀéÉêÊíÍóÓôÔõÕúÚçÇ"
    outab = "__aAaAaAaAeEeEiIoOoOoOuUcC"
    ic = ic.translate(''.maketrans(intab, outab)).lower()
    return ic

def encontraNomeSimilar(df, nome):
    df['ratio'] = [fuzz.WRatio(nome, rs) for rs in df.nome]
    return df.sort_values('ratio',ascending=False)[:1].nome

def falhasNosAnos(anoInicial,df):
    falhas = 99999    
    anoAtual = datetime.today().year
    if not df.empty:
        sr = pd.concat([df.data.dt.year,pd.Series([anoInicial,anoAtual])]).sort_values()
        anosr = sr.drop_duplicates().diff().iloc[1:]
        falhas = anosr[anosr != 1].sum()
    return falhas
    
def criaInstanciaModelo(modelo, linha, columns):
    novo_reg = {}
    for campo in modelo._meta.fields:
        if campo.attname in columns:
            novo_reg[campo.attname] = linha[campo.attname] 
    return novo_reg

def ajustaEscalaTabelaCVM(x):
    if x.escala_moeda == 'MIL':
        if hasattr(x,'resultado_antes_tributos_sobre_lucro'): x.resultado_antes_tributos_sobre_lucro *= 1000
        if hasattr(x,'lucro_prejuizo_consolidado_periodo'): x.lucro_prejuizo_consolidado_periodo *= 1000 
        if hasattr(x,'resultado_liquido_operacoes_continuadas'): x.resultado_liquido_operacoes_continuadas *= 1000
    return x

class Setor(models.Model):
    nome = models.CharField(max_length=200,db_index=True,unique=True)

    class Meta:
        ordering = ['nome']

class SubSetor(models.Model):
    nome = models.CharField(max_length=200,db_index=True)
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE,db_index=True)

    class Meta:
        unique_together = [['setor', 'nome']]
        ordering = ['nome']

class Segmento(models.Model):
    nome = models.CharField(max_length=200,db_index=True)
    subsetor = models.ForeignKey(SubSetor, on_delete=models.CASCADE,db_index=True)

    class Meta:
        unique_together = [['subsetor', 'nome']]
        ordering = ['nome']

class Empresa(models.Model):
    nome = models.CharField(max_length=200,db_index=True, unique=True)
    segmento = models.ForeignKey(Segmento, on_delete=models.CASCADE,db_index=True)
    codigo = models.CharField(max_length=10)
    tipo_periodo = models.CharField(max_length=3,db_index=True,default='3M')
    ativo = models.BooleanField(default=True)
    classificacao = models.CharField(max_length=10,default='   ')
    TIPO_INVESTIMENTO = (
            ('B', 'Bolsa'),
            ('D', 'Debênture'),
            ('O', 'Outros'),
        )
    tipo_investimento = models.CharField(max_length=1, choices=TIPO_INVESTIMENTO, default='B')     
    denominacao = models.CharField(max_length=200,default='')
    cnpj = models.CharField(max_length=20,default='')
    cod_cvm = models.IntegerField(default=0)
    denom_comerc     = models.CharField(max_length=100,default='')
    dt_reg   = models.DateTimeField('data',default='1900-01-01')
    dt_const         = models.DateTimeField('data',default='1900-01-01')
    setor_ativ       = models.CharField(max_length=100,default='')
    categ_reg        = models.CharField(max_length=100,default='')
    dt_ini_categ     = models.DateTimeField('data',default='1900-01-01')
    sit_emissor      = models.CharField(max_length=100,default='')
    dt_ini_sit_emissor       = models.DateTimeField('data',default='1900-01-01')
    controle_acionario       = models.CharField(max_length=100,default='')
    tp_ender         = models.CharField(max_length=100,default='')
    logradouro       = models.CharField(max_length=100,default='')
    compl    = models.CharField(max_length=100,default='')
    bairro   = models.CharField(max_length=100,default='')
    mun      = models.CharField(max_length=100,default='')
    uf       = models.CharField(max_length=100,default='')
    pais     = models.CharField(max_length=100,default='')
    cep      = models.CharField(max_length=100,default='')
    ddd_tel  = models.CharField(max_length=100,default='')
    tel      = models.CharField(max_length=100,default='')
    email    = models.CharField(max_length=100,default='')
    tp_resp  = models.CharField(max_length=100,default='')
    resp     = models.CharField(max_length=100,default='')
    dt_ini_resp      = models.DateTimeField('data',default='1900-01-01')
    logradouro_resp  = models.CharField(max_length=100,default='')
    compl_resp       = models.CharField(max_length=100,default='')
    bairro_resp      = models.CharField(max_length=100,default='')
    mun_resp         = models.CharField(max_length=100,default='')
    uf_resp  = models.CharField(max_length=100,default='')
    pais_resp        = models.CharField(max_length=100,default='')
    cep_resp         = models.CharField(max_length=100,default='')
    ddd_tel_resp     = models.CharField(max_length=100,default='')
    tel_resp         = models.CharField(max_length=100,default='')
    email_resp       = models.CharField(max_length=100,default='')
    cnpj_auditor     = models.CharField(max_length=100,default='')
    auditor  = models.CharField(max_length=100,default='')
    
    class Meta:
        ordering = ['nome']

    @property
    def crescimento(self):
        indice = None
        coluna = 'resultado_antes_tributos_sobre_lucro'
        # Carrega os dados dos resultados por trimestre / ano (tipo_periodo)
        df = pd.DataFrame(self.cvmresultado_set.filter(Q(tipo_periodo=self.tipo_periodo)).values('data_fim_exercicio',coluna).order_by('-data_fim_exercicio'))
        if not df.empty:
            df = df.rename(columns={'data_fim_exercicio':'data'}).reset_index(drop=True)
            # Agrupa o resultado em 4 trimestres para compatibilizar com os resultados anuais / sazonais
            if self.tipo_periodo == '3M':
                df['valor'] = [df[coluna].iloc[idx:idx+4:].sum() for idx in df.index]
                df = df[-4::-1].drop(columns=[coluna]).reset_index(drop=True)        
            # Ignorar as empresas que não tem resultado no ano anterior ou corrente
            if not df.empty:
                if df.data.dt.year.iloc[-1] >= anoAnterior:
                    # Ignorar as empresas que tiverem 40% dos últimos 5 resulados negativos
                    if len(df.iloc[-5:][df.iloc[-5:].valor <= 0]) / len(df.iloc[-5:]) <= 0.4:
                        df['pctchange'] = df.valor.pct_change() 
                        indice = df.valor.ewm(alpha=0.7).mean().iloc[-1] / df.valor.ewm(alpha=0.7).std().iloc[-1]
                        if indice == 0: indice = None 
        return indice

    @property
    def consistencia(self):
        indice = None
        colunas = ['lucro_prejuizo_consolidado_periodo','resultado_liquido_operacoes_continuadas']
        df = pd.DataFrame(self.cvmresultado_set.filter(tipo_periodo=self.tipo_periodo).values('data_fim_exercicio',colunas[0],colunas[1]).order_by('-data_fim_exercicio'))
        if df[df[colunas[0]] != 0].empty:
            df.drop(columns=colunas[0],inplace=True)
            coluna = colunas[1]
        else:
            df.drop(columns=colunas[1],inplace=True)
            coluna = colunas[0]
        if not df.empty:
            df = df.rename(columns={'data_fim_exercicio':'data'}).reset_index(drop=True)
            if self.tipo_periodo == '3M':
                df['soma'] = [df[coluna].iloc[idx:idx+4:].sum() for idx in df.index]
                df = df[-4::-1].drop(columns=[coluna]).rename(columns={'soma':coluna}).reset_index(drop=True)
            if not df.empty:
                df = df.rename(columns={coluna: 'valor'})
                # Ignorar as empresas que não tem resultado no ano anterior ou corrente
                if df.data.dt.year.iloc[-1] >= anoAnterior:
                    # Ignorar as empresas que tiverem 40% dos últimos 5 resulados negativos
                    if len(df.iloc[-5:][df.iloc[-5:].valor <= 0]) / len(df.iloc[-5:]) <= 0.4:
                        df['pctchange'] = df.valor.pct_change() 
                        indice = df.valor.ewm(alpha=0.1).mean().iloc[-1] / df.valor.ewm(alpha=0.1).std().iloc[-1]
                        if indice == 0: indice = None
        return indice

    @property
    def robustez(self):
        indice = None
        # coluna = 'resultado_liquido_operacoes_continuadas'
        coluna = 'resultado_antes_tributos_sobre_lucro'
        # Identifica qual o campo do Balanço Passivo que contém o valor do Patrimônio Líquido
        qs = CVMCampo.objects.filter(Q(tabela__modelo='CVMBalancoPassivo')&(Q(cvmcamponome__empresas__id=self.id)&Q(cvmcamponome__nome__contains='Patrimônio Líquido')))
        colunaPL = qs.first().campo if qs.exists() else 'patrimonio_liquido_consolidado'
        # Identifica as empresas que na conta 1.02 contabilizam o Ativo Não Circulante ou Ativos Financeiros e atribui a colunaCX os campos correspondentes para calculo da Disponibilidade
        colunaCX = ('caixa_equivalentes_caixa','aplicacoes_financeiras') if CVMCampo.objects.filter(Q(tabela__modelo='CVMBalancoAtivo')&Q(codigo='1.02')&(Q(cvmcamponome__empresas__id=self.id)&Q(cvmcamponome__nome__contains='Ativo Não Circulante'))).exists() else ('ativo_circulante','ativo_nao_circulante') 
        # Carrega os dados dos resultados por trimestre / ano (tipo_periodo)
        df = pd.DataFrame(self.cvmresultado_set.filter(Q(tipo_periodo=self.tipo_periodo)).values('data_fim_exercicio',coluna).order_by('-data_fim_exercicio'))
        if not df.empty:
            df = df.rename(columns={'data_fim_exercicio':'data'}).reset_index(drop=True)
            if self.tipo_periodo == '3M':
                df['soma'] = [df[coluna].iloc[idx:idx+4:].sum() for idx in df.index]
                df = df[-4::-1].drop(columns=[coluna]).rename(columns={'soma':coluna}).reset_index(drop=True)
            dfBA = pd.DataFrame(self.cvmbalancoativo_set.filter(Q(tipo_periodo=self.tipo_periodo)).annotate(disponibilidade=F(colunaCX[0]) + F(colunaCX[1])).values('data_fim_exercicio','disponibilidade').order_by('data_fim_exercicio'))
            dfBP = pd.DataFrame(self.cvmbalancopassivo_set.filter(Q(tipo_periodo=self.tipo_periodo)).annotate(divida=F('emprestimos_financiamentos') + F('emprestimos_financiamentos1')).values('data_fim_exercicio','divida',colunaPL).order_by('data_fim_exercicio'))
            if not dfBA.empty: df = df.merge(dfBA.rename(columns={'data_fim_exercicio':'data'}), how='inner', left_on='data', right_on='data')
            else: df['disponibilidade'] = 0
            if not dfBP.empty: df = df.merge(dfBP.rename(columns={'data_fim_exercicio':'data'}), how='inner', left_on='data', right_on='data')
            else: df['divida'],df[colunaPL] = 0,0
        if not df.empty:
            df = df.rename(columns={coluna: 'receita',colunaPL:'patrimonio_liquido'})
            df['disponibilidade_liquida'] = df.disponibilidade - df.divida
            if df.data.dt.year.iloc[-1] >= anoAnterior:
                df['media_receita'] =  df.receita.ewm(alpha=0.7).mean()
                df['media_disponibilidade_liquida'] =  df.disponibilidade_liquida.ewm(alpha=0.7).mean()
                if df.media_receita.iloc[-1] > 0 and df.media_disponibilidade_liquida.iloc[-1] < 0:
                    # Empresas com dívida, calcular relação dívida / receita
                    indice = df.media_disponibilidade_liquida.iloc[-1] / df.media_receita.iloc[-1] 
                elif df.media_disponibilidade_liquida.iloc[-1] >= 0:
                    # Empresas sem dívida, calcular relação receita / petrimônio líquido
                    df['media_patrimonio_liquido'] =  df.patrimonio_liquido.ewm(alpha=0.7).mean()
                    indice = df.media_receita.iloc[-1] / df.media_patrimonio_liquido.iloc[-1] if df.media_receita.iloc[-1] > 0 else None
        return indice

class Cotacao(models.Model):
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)
    data = models.DateTimeField('data',default='2022-01-01',db_index=True)
    abertura = models.FloatField(default=0)
    fechamento = models.FloatField(default=0)
    minimo = models.FloatField(default=0)
    maximo = models.FloatField(default=0)
    volume = models.FloatField(default=0)
    dividendos = models.FloatField(default=0)
    divisao = models.FloatField(default=0)
    preco_ajustado = models.FloatField(default=0)

    class Meta:
        unique_together = [['acao', 'data']]
        ordering = ['acao','-data']

class CotacaoIntraDia(models.Model):
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)
    data = models.DateTimeField('data',db_index=True)
    abertura = models.FloatField(default=0)
    fechamento = models.FloatField(default=0)
    minimo = models.FloatField(default=0)
    maximo = models.FloatField(default=0)
    volume = models.FloatField(default=0)
    dividendos = models.FloatField(default=0)
    divisao = models.FloatField(default=0)
    preco_ajustado = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cotacao_intra_dia'
        unique_together = [['acao', 'data']]
        ordering = ['acao','-data']

class PerfilCarteira(models.Model):
    nome = models.CharField(max_length=40, unique=True)
    ordem = models.IntegerField(default=0)    

    class Meta:
        db_table = 'home_perfil_carteira'
        ordering = ['ordem']

class TipoCarteira(models.Model):
    nome = models.CharField(max_length=40)    
    perfil = models.ForeignKey(PerfilCarteira, on_delete=models.CASCADE)
    ordem = models.IntegerField(default=0)

    class Meta:
        db_table = 'home_tipo_carteira'
        unique_together = [['perfil', 'nome']]
        ordering = ['ordem']

class Carteira(models.Model):
    tipo_carteira = models.ForeignKey(TipoCarteira, on_delete=models.CASCADE,db_index=True)
    data = models.DateTimeField('data',db_index=True)

    class Meta:
        unique_together = [['tipo_carteira', 'data']]
        ordering = ['tipo_carteira','-data']


class ProjecaoAcao(models.Model):
    projecao = models.ForeignKey('Projecao', on_delete=models.CASCADE,db_index=True,default=1)
    carteira = models.ManyToManyField(Carteira,db_index=True)
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)
    tipo = models.CharField(max_length=10)
    preco_ia = models.FloatField(default=0)
    data_preco_ia  = models.DateTimeField('data',default='2022-01-01 00:00:00-03')
    preco_corrente = models.FloatField(default=0)
    preco_medio = models.FloatField(default=0)
    preco_compra = models.FloatField(default=0)
    preco_venda = models.FloatField(default=0)
    preco_venda_maximo = models.FloatField(default=0)
    rentabilidade = models.FloatField(default=0,db_index=True)
    rentabilidade_maxima = models.FloatField(default=0,db_index=True)
    dias_operacao_compra = models.IntegerField(default=0)
    dias_operacao_venda = models.IntegerField(default=0)
    votos = models.IntegerField(default=0)
    tempo_projecao = models.FloatField(default=0)

    class Meta:
        db_table = 'home_projecao_acao'
        unique_together = [['projecao', 'acao']]
        ordering = ['-projecao','acao']

    def rankear_rankings(self, ordem):
        indice = None
        ordem_rankings = CategoricalDtype(ordem,ordered=True)
        df = pd.DataFrame(self.rankeamento_set.filter(ranking_id__in=ordem_rankings.categories).values('ranking_id','indice_rank'))
        if not df.empty:
            df['ranking_id'] = df['ranking_id'].astype(ordem_rankings)
            df.sort_values('ranking_id',ascending=False,inplace=True)
            indice = df.indice_rank.ewm(alpha=0.5).mean().iloc[-1]
            if indice==0: indice = None
        return indice

    @property
    def rentabilidade_obtida(self):
        cotacao = Cotacao.objects.filter(Q(acao=self.acao) & Q(data__lte=(self.projecao.data + timedelta(days=self.dias_operacao)))).values_list('fechamento','data')[0]
        return round((cotacao[0] / self.preco_compra - 1) * 100,0) if self.preco_compra > 0 else 0

    @property
    def dias_operacao(self):
        return self.dias_operacao_compra if self.tipo == 'Compra' else self.dias_operacao_venda

    @property
    def dias_transcorridos(self):
        trans = (self.acao.cotacao_set.all()[:1][0].data - self.projecao.data).days
        return trans if trans < self.dias_operacao else self.dias_operacao

    @property
    def final_operacao(self):        
        return (self.projecao.data + timedelta(days=self.dias_operacao)).strftime("%d %b, %y")

    def rankearAcao(self):
        return True

class CotacaoIndice(models.Model):
    indice = models.ForeignKey('Indice', on_delete=models.CASCADE, default=6,db_index=True)
    data = models.DateTimeField('data',default='2022-01-01',db_index=True)
    valor = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cotacao_indice'
        unique_together = [['indice', 'data']]
        ordering = ['indice', '-data']
    
class Indice(models.Model):
    codigo = models.CharField(max_length=20, unique=True)    
    TIPO_PERIODO = (
            ('D', 'Diário'),
            ('M', 'Mensal'),
            ('A', 'Anual'),
        )
    periodicidade = models.CharField(max_length=1, choices=TIPO_PERIODO)   
    indice_bcb = models.IntegerField(default=0,null=True)

    class Meta:
        db_table = 'home_indice'
        ordering = ['codigo']

    def atualizarDadosBCB(self): 
        try:
            dtInicio = self.cotacaoindice_set.filter(indice=self.pk).values_list('data').aggregate(Max('data'))['data__max']
            dtInicio = '2000-01-01' if dtInicio is None else dtInicio.strftime("%Y-%m-%d")
            df = pd.DataFrame(sgs.get({'valor': self.indice_bcb}, start=dtInicio)).reset_index().rename(columns={'Date': 'data'})[['data','valor']][1:]
            df.data = pd.to_datetime(df.data,utc=True,infer_datetime_format=True)
            df.drop_duplicates(subset=['data'],keep='last',inplace=True)
            df['indice_id'] = self.pk
            novas_instancias = [CotacaoIndice(**criaInstanciaModelo(CotacaoIndice,linha,df.columns)) for idx_ii,linha in df.iterrows()]
            CotacaoIndice.objects.bulk_create(novas_instancias)

        except Exception as exceptionObj:
            estado = exceptionObj.args[0]
            print(f'Erro {estado}')
    
    def importarDados(self):
        print(self.codigo)
        if self.indice_bcb: 
            self.atualizarDadosBCB()
        # self.atualizarDadosTreasury()

def prepararIndicesAnalise():
    df = pd.DataFrame()
    # for indice in Indice.objects.all():
    for indice in Indice.objects.exclude(codigo__icontains='treasury'):
        cotacao = pd.DataFrame(indice.cotacaoindice_set.all().values())
        if not cotacao.empty:
            if len(df) == 0:
                df['data'] = cotacao.data
                df[indice.codigo] = cotacao.valor
            else:
                df = df.merge(cotacao[['data','valor']], how='outer', left_on='data', right_on='data')
                df.rename(columns={'valor': indice.codigo}, inplace=True)
    df.sort_values(by=['data'],inplace=True)
    return df

def atualizarDadosTreasury():
    paises = bonds.get_bond_countries()
    print(paises)
    titulos = bonds.get_bonds(country='united states')
    print(titulos)
    repetir = True
    while repetir: 
        try:
            registro = bonds.get_bond_historical_data(bond='U.S. 5Y', from_date='01/09/2022', to_date='30/09/2022')
            print(registro)
            repetir = False

        except Exception as exceptionObj:
            estado = exceptionObj.args[0]
            print('Erro ' + estado)
            repetir = True
    # return df

def atualizarDadosTesouro():
    try:
        df = pd.read_csv('https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv',
                sep=";", 
                decimal=",", 
                thousands=".", 
                # dtype={'valor': float64},       
                parse_dates=['Data Vencimento','Data Base'], dayfirst=True)
        df = df[df['Tipo Titulo'] == 'Tesouro Prefixado']
        df = pd.DataFrame({'data': df['Data Base'], 'dias': df['Data Vencimento'] - df['Data Base'], 'valor': df['Taxa Compra Manha']})
        df['codigo'] = ''
        for index, item in df.iterrows():
            if item.dias.days <= 30:
                tipo = '1m'
            elif item.dias.days <= 60:
                tipo = '2m'
            elif item.dias.days <= 90:
                tipo = '3m'
            elif item.dias.days <= 180:
                tipo = '6m'
            elif item.dias.days <= 365:
                tipo = '1a'
            elif item.dias.days <= 365*2:
                tipo = '2a'
            elif item.dias.days <= 365*3:
                tipo = '3a'
            elif item.dias.days <= 365*5:
                tipo = '5a'
            elif item.dias.days <= 365*10:
                tipo = '10a'
            else:
                tipo = str(item.dias.days)
            df.loc[index,'codigo'] = 'tesouro' + tipo
        df.drop(columns=['dias'],inplace=True)
        df.set_index(['codigo'],inplace=True)
        for codigo in df.index.unique(0):
            print(codigo)
            indice = Indice.objects.get(codigo=codigo)
            if indice:
                dtInicio = indice.cotacaoindice_set.all().values_list('data').aggregate(Max('data'))['data__max']
                dtInicio = '2000-01-01' if dtInicio is None else dtInicio.strftime("%Y-%m-%d")
                df_aux = df.loc[codigo]
                df_aux = df_aux[df_aux.data > dtInicio].copy()
                df_aux.data = pd.to_datetime(df_aux.data,utc=True,infer_datetime_format=True)
                df_aux.drop_duplicates(subset=['data'],keep='last',inplace=True)
                df_aux['indice_id'] = indice.id
                novas_instancias = [CotacaoIndice(**criaInstanciaModelo(CotacaoIndice,linha,df_aux.columns)) for idx_ii,linha in df_aux.iterrows()]
                CotacaoIndice.objects.bulk_create(novas_instancias)
                
    except Exception as exceptionObj:
        estado = exceptionObj.args[0]
        print('Erro ' + estado)
    return df
        
class DadosGrafico:    
    def __init__(self, df, sufixo='', sobreposto=False, indices=[], rentabilidade=0, faixas={}):
        self.df = df.fillna(0)
        self.sufixo = sufixo
        self.sobreposto = sobreposto
        self.indices = indices
        self.rentabilidade = rentabilidade
        self.faixas = faixas
        
        if len(self.indices) > 0:
            for col in self.indices:
                valorInicial = 100
                for idx,item in self.df[col].items():
                    self.df.loc[idx,col] = valorInicial
                    valorInicial = round(valorInicial * (1 + item/100),2)

    @property
    def eixoXCategorias(self):
        lista = self.df.index.get_level_values(0).to_list()
        if isinstance(lista[0], datetime):
            lista = [int(dt.timestamp())*1000 for dt in lista]
        return lista

    @property
    def eixoY(self):
        if self.sobreposto:
            yAxis = {'max': round(max(self.df.apply(np.sum,1)) * 1.1,2)}  
        elif len(self.faixas) > 0:
            vMin = self.df.min()[0]
            if vMin > self.faixas.iloc[0].valor_inicial: vMin = self.faixas.iloc[0].valor_inicial
            vMax = self.df.max()[0]
            if vMax < self.faixas.iloc[1].valor_final: vMax = self.faixas.iloc[1].valor_final
            yAxis = {'min': round(vMin * 0.99,2),'max': round(vMax * 1.01,2)}
        else: # len(self.df.columns) > 1:
            yAxis = [{'show': False, 'forceNiceScale': True, 'id': c, 'show': False, 'min': round(self.df[c].min() * 0.99,2),'max': round(self.df[c].max() * 1.01,2)} for c in self.df.columns]
        # else:
        #     yAxis = {'min': round(min(self.df.min()) * 0.99,2),'max': round(max(self.df.max()) * 1.01,2)}
        # print(yAxis)
        return yAxis

    # @property
    def dadosSeries(self):
        if len(self.faixas) > 0 and not self.sobreposto:
            serie = [{'name': c + self.sufixo, 'data': self.df[c].to_list()} for c in self.df.columns]
        else:
            serie = [{'yAxisID': c, 'name': c + self.sufixo, 'data': self.df[c].to_list()} for c in self.df.columns]
        # print(serie)
        return serie

    # @property
    def dadosSeriesDonut(self):
        return self.df[self.df.columns[0]].to_list()
    
    # @property
    def notasTotalX(self):
        return [{'x': i,
                 'label': {
                     'text': "Total: " + '{valor:.2f}'.format(valor=round(r.sum(),2)),
                     'orientation': "horizontal",
                     'style': {
                        'color': "#fff",
                        'background': "#000"
                        },
                    }
                 } for i, r in self.df.iterrows()]    

    # @property
    def notasFaixasY(self):
        if len(self.faixas) > 0:
            vMin = self.df.min()[0]
            if vMin < self.faixas.loc[0,'valor_inicial']: self.faixas.loc[0,'valor_inicial'] = vMin
            vMax = self.df.max()[0]
            if vMax > self.faixas.loc[1,'valor_final']: self.faixas.loc[1,'valor_final'] = vMax
        yaxis,xaxis,points = [],[],[]
        for idx,it in self.faixas.iterrows():
            yaxis.append({                                    
                        'y': it.valor_inicial,
                        'y2': it.valor_final,
                        'borderColor': "#e6e6e6",
                        'fillColor': "#e6e6e6",
                        'opacity': 0.7,
                        'width': '100%',})
            xaxis.append({
                        'x': self.eixoXCategorias[round(len(self.eixoXCategorias)/2)],
                        'borderColor': '#e6e6e6',
                        'fillColor': '#e6e6e6',
                        'opacity': 0.3,
                        'offsetX': 0,
                        'offsetY': 0,
                        'label': {
                            'borderColor': '#e6e6e6',
                            'borderWidth': 1,
                            'borderRadius': 2,
                            'text': it.nome,
                            'textAnchor': 'middle',
                            'position': it.posicao,
                            'orientation': 'horizontal',                
                            'offsetY': it.offsetY,
                            'style': {
                                'fontSize': "11px",
                                'fontWeight': 600,
                                'color': "#333",
                                'background': "#e6e6e6"
                            },                            
                        },
                    })
            points.append({
                        'x': self.eixoXCategorias[0],
                        'y': it.valor_inicial,
                        'marker': {
                            'size': 4,
                            'fillColor': "#fff",
                            'strokeColor': "black",
                            'radius': 2,
                            'cssClass': "apexcharts-custom-class"
                        },
                        'label': {
                            'borderColor': "#e6e6e6",
                            'offsetY': 40,
                            'style': {
                                'fontSize': "13px",
                                'fontWeight': 600,
                                'color': "#333",
                                'background': "#e6e6e6"
                            },
                            'text': '{valor:.2f}'.format(valor=it.valor_inicial),
                            'textAnchor': 'start',
                        },
                    })
            points.append({        
                        'x': self.eixoXCategorias[len(self.eixoXCategorias)-1],
                        'y': it.valor_final,
                        'marker': {
                            'size': 4,
                            'fillColor': "#fff",
                            'strokeColor': "black",
                            'radius': 2,
                            'cssClass': "apexcharts-custom-class"
                        },
                        'label': {
                            'borderColor': "#e6e6e6",
                            'offsetY': 40,
                            'style': {
                                'fontSize': "13px",
                                'fontWeight': 600,
                                'color': "#333",
                                'background': "#e6e6e6"
                            },
                            'text': '{valor:.2f}'.format(valor=it.valor_final),
                            'textAnchor': 'end',
                        },
                    })
        notas = {
            'position': 'front',
            'yaxis': yaxis,
            'xaxis': xaxis,
            'points': points}
        return notas

    # @property
    def rentabilidadeRelativa(self):
        s2 = self.df[self.df.columns[2]]
        c2 = ((s2[len(s2)-1]/s2[0])-1)*100
        return round((self.rentabilidade/c2)*100,0) if c2 > 0 else None

class PlanoAcesso(models.Model):
    descricao = models.CharField(max_length=255)
    class Meta:
        db_table = 'home_plano_acesso'

class Plano(models.Model):
    nome = models.CharField(max_length=30,db_index=True, unique=True)
    valor = models.FloatField(default=0)
    desabilitar_configuracao = models.BooleanField(default=True)

class PlanoAcessoPlano(models.Model):
    plano = models.ForeignKey(Plano, on_delete=models.CASCADE, default=1)
    plano_acesso = models.ForeignKey(PlanoAcesso, on_delete=models.CASCADE, default=1)
    ativo = models.BooleanField(default=True)
    class Meta:
        db_table = 'home_plano_acesso_plano'
        unique_together = [['plano','plano_acesso']]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    projecaoacao = models.ForeignKey(ProjecaoAcao, on_delete=models.DO_NOTHING, default=1)
    plano = models.ForeignKey(Plano, on_delete=models.DO_NOTHING, default=1)
    primeiro_nome = models.CharField(max_length=30, null=True)
    ultimo_nome = models.CharField(max_length=30, null=True)
    TIPO_PERFIL = (
        ('a', 'Agressivo'),
        ('m', 'Moderado'),
        ('c', 'Conservador'),
    )
    perfil = models.CharField(max_length=1, choices=TIPO_PERFIL, default='m')     
    celular = models.CharField(max_length=20, null=True)
    email = models.EmailField(max_length=254, null=True)
    endereco = models.CharField(max_length=254, null=True)
    menu_acao = models.BooleanField(default=False)
    menu_empresa = models.BooleanField(default=False)
    menu_favorito = models.BooleanField(default=False)
    menu_setor = models.BooleanField(default=False)
    menu_projecao = models.BooleanField(default=False)
    menu_ranking = models.BooleanField(default=False)
    menu_robo = models.BooleanField(default=True)
    menu_esconder_inativos = models.BooleanField(default=False)
    TIPO_PROJECAO = (
        ('u', 'Últimas'),
        ('n', 'Penúltima'),
        ('p', 'Período'),
    )
    projecao_smallcap = models.BooleanField(default=False)
    projecao_tipo = models.CharField(max_length=1, choices=TIPO_PROJECAO, default='n')     
    projecao_ultimas = models.IntegerField(default=1)
    projecao_periodo_inicio = models.DateField('Início',default='2022-01-01',db_index=True)
    projecao_periodo_fim = models.DateField('Fim',default='2022-01-01',db_index=True)
    ranking_rankeados = models.IntegerField(default=5)

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            try:
                rankingPadrao = 3
                p = Profile.objects.create(user=instance)
                for r in Ranking.objects.filter(visivel=True):
                    ProfileRanking(ranking=r, profile=p, pranking_visivel=True if r.id == rankingPadrao else False).save()   
                projecao = Projecao.objects.all().order_by('-data')[1:2:]
                if projecao.exists():
                    p.projecaoacao = projecao[0].projecaoacao_set.filter(rankeamento__ranking__id=rankingPadrao).annotate(rank=Max('rankeamento__indice_rank')).order_by('-rank').first()
            except Exception as exceptionObj:
                print(exceptionObj.args)

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()

class ProfileFavorito(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE,db_index=True)
    acao = models.ForeignKey('Acao', on_delete=models.CASCADE)
    class Meta:
        db_table = 'home_profile_favorito'
        unique_together = [['profile','acao']]
class ProfileRanking(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE,db_index=True)
    ranking = models.ForeignKey('Ranking', on_delete=models.CASCADE)
    pranking_visivel = models.BooleanField(default=False)

    # def __str__(self):
    #     return self.pranking_visivel
    class Meta:
        db_table = 'home_profile_ranking'
        unique_together = [['profile','ranking']]
        # ordering = ['campo','nome']

class ResultadoImportacao(models.Model):
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)     
    data     =      models.DateTimeField('data',db_index=True)
    repeticoes       =      models.IntegerField(default=0)
    resultado        =      models.CharField(max_length=350)
    modelo   =      models.CharField(max_length=250, default='sem nome')

    class Meta:
        db_table = 'home_resultado_importacao'
        unique_together = [['acao', 'data', 'modelo']]
        ordering = ['acao', '-data']

class ResultadoAnaliseImportacao(models.Model):
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)     
    ano     =      models.IntegerField(default=0)
    quantidade        =      models.IntegerField(default=0)
    modelo   =      models.CharField(max_length=250, default='sem nome')
    tipo_periodo   =      models.CharField(max_length=10, default='')
    codigo_moeda   =      models.CharField(max_length=10, default='')
    TIPO_PROBLEMA = (
            ('F', 'Falta'),
            ('D', 'Duplicidade'),
        )
    tipo_problema = models.CharField(max_length=1, choices=TIPO_PROBLEMA, default='F')   


    class Meta:
        db_table = 'home_resultado_analise_importacao'
        unique_together = [['acao', 'ano', 'modelo', 'tipo_periodo', 'codigo_moeda']]
        ordering = ['acao', 'modelo', 'tipo_periodo', 'codigo_moeda', 'ano']

class CampoTraduzido(models.Model):
    modelo      =      models.CharField(max_length=250,db_index=True, default='sem nome')
    original    =      models.CharField(max_length=100,db_index=True)
    traduzido   =      models.CharField(max_length=250)

    class Meta:
        db_table = 'home_campo_traduzido'
        unique_together = [['modelo', 'original'],['modelo', 'traduzido']]
        ordering = ['modelo', 'original']

class CampoInexistente(models.Model):
    modelo      =      models.CharField(max_length=250,db_index=True, default='sem nome')
    original    =      models.CharField(max_length=100,db_index=True)
    traduzido   =      models.CharField(max_length=250)
    codigo      =      models.CharField(max_length=500, default='')

    class Meta:
        db_table = 'home_campo_inexistente'
        unique_together = [['modelo', 'original']]
        ordering = ['modelo', 'original']
        
class ParametroImportacao(models.Model):
    ajustar_numero   =      models.BooleanField(default=False)
    atualizar        =      models.BooleanField(default=False)
    biblioteca       =      models.CharField(max_length=10, null=True)
    campo_filtro_importados  =      models.CharField(max_length=250, null=True)
    campos_select    =      models.CharField(max_length=250, null=True)
    chave_e_parametro        =      models.BooleanField(default=False)
    codigo_e_parametro       =      models.BooleanField(default=False)
    complemento_sql  =      models.CharField(max_length=250, null=True)
    existe_tabela    =      models.BooleanField(default=False)
    filtro_importados        =      models.CharField(max_length=250, null=True)
    hora_liberado    =      models.TimeField(default='18:00:00-03')
    importados_rename        =      models.CharField(max_length=250, null=True)
    index_registros  =      models.CharField(max_length=250, null=True)
    intra_dia        =      models.BooleanField(default=False)
    metodo_ticker    =      models.CharField(max_length=250, null=True)
    obs      =      models.CharField(max_length=250, null=True)
    parametro_ticker1        =      models.CharField(max_length=250, null=True)
    parametro_ticker2        =      models.CharField(max_length=250, null=True)
    parametro_ticker3        =      models.CharField(max_length=250, null=True)
    periodo_atualizacao      =      models.FloatField(default=0)
    sufixo   =      models.CharField(max_length=5)
    modelo   =      models.CharField(max_length=250, null=True)
    traduzir         =      models.BooleanField(default=False)
    transpor        =      models.BooleanField(default=False)

    class Meta:
        db_table = 'home_parametro_importacao'
        ordering = ['modelo']

class Balanco(models.Model): 
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)     
    data = models.DateTimeField('data',default='2022-01-01',db_index=True)
    acao_emitida     =      models.FloatField(default=0)
    acao_ordinaria   =      models.FloatField(default=0)
    acoes_em_tesouraria      =      models.FloatField(default=0)
    acoes_ordinarias         =      models.FloatField(default=0)
    acoes_preferenciais      =      models.FloatField(default=0)
    acoes_preferenciais_equidade    =      models.FloatField(default=0)
    ajustes_de_conversao_de_moeda_estrangeira        =      models.FloatField(default=0)
    arrendamentos    =      models.FloatField(default=0)
    ativo_diferido_nao_circulante    =      models.FloatField(default=0)
    ativos_correntes         =      models.FloatField(default=0)
    ativos_de_impostos_diferidos_atuais      =      models.FloatField(default=0)
    ativos_de_impostos_diferidos_nao_correntes       =      models.FloatField(default=0)
    ativos_diferidos_atuais  =      models.FloatField(default=0)
    ativos_financeiros       =      models.FloatField(default=0)
    ativos_financeiros_designados_ao_valor_justo_pelo_result_total  =      models.FloatField(default=0)
    ativos_mantidos_para_venda_atuais        =      models.FloatField(default=0)
    ativos_pre_pagos         =      models.FloatField(default=0)
    ativos_pre_pagos_nao_circulantes         =      models.FloatField(default=0)
    ativos_tangiveis_liquidos        =      models.FloatField(default=0)
    ativos_totais    =      models.FloatField(default=0)
    beneficio_de_pensao_definido     =      models.FloatField(default=0)
    beneficios_do_empregado  =      models.FloatField(default=0)
    boa_vontade      =      models.FloatField(default=0)
    caixa_e_equivalentes_de_caixa    =      models.FloatField(default=0)
    capital_adicional_pago   =      models.FloatField(default=0)
    capital_de_giro  =      models.FloatField(default=0)
    capital_investido        =      models.FloatField(default=0)
    capital_social   =      models.FloatField(default=0)
    capital_total_parceria   =      models.FloatField(default=0)
    capitalizacao_total      =      models.FloatField(default=0)
    cobertura_de_ativos_atuais       =      models.FloatField(default=0)
    codigo_moeda     =      models.CharField(max_length=60)
    construcao_em_progresso  =      models.FloatField(default=0)
    construcoes_e_melhorias  =      models.FloatField(default=0)
    contas_a_pagar   =      models.FloatField(default=0)
    contas_a_pagar_comerciais_e_outras_nao_correntes         =      models.FloatField(default=0)
    contas_a_pagar_e_despesas_acumuladas     =      models.FloatField(default=0)
    contas_a_receber         =      models.FloatField(default=0)
    contas_a_receber_bruto   =      models.FloatField(default=0)
    contas_a_receber_nao_correntes   =      models.FloatField(default=0)
    depreciacao_acumulada    =      models.FloatField(default=0)
    despesas_acumuladas_atuais       =      models.FloatField(default=0)
    despesas_acumuladas_nao_correntes        =      models.FloatField(default=0)
    devido_a_partes_relacionadas_atuais      =      models.FloatField(default=0)
    devido_a_partes_relacionadas_nao_circulantes     =      models.FloatField(default=0)
    devido_de_partes_relacionadas_atuais     =      models.FloatField(default=0)
    dinheiro_financeiro      =      models.FloatField(default=0)
    dinheiro_restrito        =      models.FloatField(default=0)
    disposicoes_atuais       =      models.FloatField(default=0)
    disposicoes_de_longo_prazo       =      models.FloatField(default=0)
    divida_atual     =      models.FloatField(default=0)
    divida_atual_e_obrigacao_de_arrendamento_de_capital      =      models.FloatField(default=0)
    divida_de_longo_prazo    =      models.FloatField(default=0)
    divida_de_longo_prazo_e_obrigacao_de_arrendamento_de_capital     =      models.FloatField(default=0)
    divida_liquida   =      models.FloatField(default=0)
    divida_total     =      models.FloatField(default=0)
    dividas_de_partes_relacionadas_nao_circulantes   =      models.FloatField(default=0)
    dividendos_pagaveis      =      models.FloatField(default=0)
    emprestimos_a_receber    =      models.FloatField(default=0)
    ppe_bruto        =      models.FloatField(default=0)
    ppe_liquido      =      models.FloatField(default=0)
    equipamentos_de_moveis_de_maquinas       =      models.FloatField(default=0)
    equivalentes_de_caixa_e_investimentos_de_curto_prazo     =      models.FloatField(default=0)
    equivalentes_em_dinheiro         =      models.FloatField(default=0)
    fundo_de_comercio_e_outros_ativos_intangiveis    =      models.FloatField(default=0)
    ganhos_perdas_que_nao_afetam_os_lucros_acumulados        =      models.FloatField(default=0)
    imposto_de_renda_a_pagar         =      models.FloatField(default=0)
    imposto_total_a_pagar    =      models.FloatField(default=0)
    impostos_a_receber       =      models.FloatField(default=0)
    interesse_minoritario    =      models.FloatField(default=0)
    inventario       =      models.FloatField(default=0)
    investimento_de_capital_de_longo_prazo   =      models.FloatField(default=0)
    investimento_em_ativos_financeiros       =      models.FloatField(default=0)
    investimento_em_joint_venture_sat_custo  =      models.FloatField(default=0)
    investimentos_e_adiantamentos    =      models.FloatField(default=0)
    investimentos_em_associados_a_custo      =      models.FloatField(default=0)
    investimentos_em_outros_empreendimentos_metodo_equiv_patrimoni  =      models.FloatField(default=0)
    investimentos_em_subsidiarias_a_custo    =      models.FloatField(default=0)
    juros_a_pagar    =      models.FloatField(default=0)
    juros_acumulados_a_receber       =      models.FloatField(default=0)
    linha_de_credito         =      models.FloatField(default=0)
    lucros_acumulados        =      models.FloatField(default=0)
    materias_primas  =      models.FloatField(default=0)
    notas_a_receber  =      models.FloatField(default=0)
    notas_atuais_a_pagar     =      models.FloatField(default=0)
    numero_de_acoes_em_tesouraria    =      models.FloatField(default=0)
    numero_de_acoes_ordinarias       =      models.FloatField(default=0)
    numero_de_acoes_preferenciais    =      models.FloatField(default=0)
    obrigacao_de_arrendamento_de_capital_atual       =      models.FloatField(default=0)
    obrigacao_de_arrendamento_de_capital_de_longo_prazo      =      models.FloatField(default=0)
    obrigacoes_de_arrendamento_de_capital    =      models.FloatField(default=0)
    outras_participacoes_societarias         =      models.FloatField(default=0)
    outras_propriedades      =      models.FloatField(default=0)
    outro_capital_social     =      models.FloatField(default=0)
    outros_a_pagar   =      models.FloatField(default=0)
    outros_ajustes_de_patrimonio     =      models.FloatField(default=0)
    outros_ativos_circulantes        =      models.FloatField(default=0)
    outros_ativos_intangiveis        =      models.FloatField(default=0)
    outros_ativos_nao_circulantes    =      models.FloatField(default=0)
    outros_creditos  =      models.FloatField(default=0)
    outros_emprestimos_correntes     =      models.FloatField(default=0)
    outros_estoques  =      models.FloatField(default=0)
    outros_investimentos     =      models.FloatField(default=0)
    outros_investimentos_de_curto_prazo      =      models.FloatField(default=0)
    outros_passivos_circulantes      =      models.FloatField(default=0)
    outros_passivos_nao_circulantes  =      models.FloatField(default=0)
    pagaveis         =      models.FloatField(default=0)
    participacao_minoritaria_bruta_do_patrimonio_liquido_total       =      models.FloatField(default=0)
    passivo_circulante       =      models.FloatField(default=0)
    passivo_diferido_nao_circulante  =      models.FloatField(default=0)
    passivo_total_participacao_minoritaria_liquida   =      models.FloatField(default=0)
    passivos_de_impostos_diferidos_atuais    =      models.FloatField(default=0)
    passivos_de_impostos_diferidos_nao_correntes     =      models.FloatField(default=0)
    passivos_de_produtos_derivativos         =      models.FloatField(default=0)
    passivos_diferidos_atuais        =      models.FloatField(default=0)
    passivos_mantidos_para_venda_nao_circulantes     =      models.FloatField(default=0)
    patrimonio_liquido       =      models.FloatField(default=0)
    perda_de_ganho_nao_realizado     =      models.FloatField(default=0)
    planos_de_pensao_nao_correntes_e_outros_planos_benef_pos_aposen  =      models.FloatField(default=0)
    previdencia_e_outros_planos_de_benef_pos_aposent_atuais  =      models.FloatField(default=0)
    produtos_acabados        =      models.FloatField(default=0)
    propriedades     =      models.FloatField(default=0)
    propriedades_de_investimento     =      models.FloatField(default=0)
    provisao_para_devedores_duvidosos        =      models.FloatField(default=0)
    provisoes_para_ajustes_de_estoques       =      models.FloatField(default=0)
    provisoes_para_ajustes_de_recebiveis     =      models.FloatField(default=0)
    recebiveis        =      models.FloatField(default=0)
    recebiveis_de_notas_nao_correntes        =      models.FloatField(default=0)
    receita_diferida_atual   =      models.FloatField(default=0)
    receita_diferida_nao_corrente    =      models.FloatField(default=0)
    reserva_de_reavaliacao_de_ativos_fixos   =      models.FloatField(default=0)
    responsabilidades_minimas_de_pensao      =      models.FloatField(default=0)
    terrenos_e_benfeitorias  =      models.FloatField(default=0)
    tipo_periodo     =      models.CharField(max_length=10,db_index=True)
    titulos_disponiveis_para_venda   =      models.FloatField(default=0)
    titulos_mantidos_ate_o_vencimento        =      models.FloatField(default=0)
    titulos_para_negociacao  =      models.FloatField(default=0)
    titulos_preferenciais_fora_do_patrimonio_liquido         =      models.FloatField(default=0)
    total_de_ativos_nao_circulantes  =      models.FloatField(default=0)
    total_do_passivo_nao_circulante  =      models.FloatField(default=0)
    trabalho_em_andamento    =      models.FloatField(default=0)
    valor_contabil_tangivel  =      models.FloatField(default=0)

    class Meta:
        unique_together = [['acao', 'data', 'tipo_periodo','codigo_moeda']]
        ordering = ['acao', '-data']
    
class DeclaracaoRenda(models.Model):  
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)     
    data = models.DateTimeField('data',default='2022-01-01',db_index=True)
    acoes_medias_basicas     =      models.FloatField(default=0)
    acoes_medias_diluidas    =      models.FloatField(default=0)
    amortizacao      =      models.FloatField(default=0)
    amortizacao_da_demonstracao_do_resultado_do_intangivel   =      models.FloatField(default=0)
    amortizacao_de_titulos   =      models.FloatField(default=0)
    codigo_moeda     =      models.CharField(max_length=60)
    custo_de_receita         =      models.FloatField(default=0)
    custo_reconciliado_da_receita    =      models.FloatField(default=0)
    declaracao_de_renda_de_depreciacao       =      models.FloatField(default=0)
    declaracao_de_rendimentos_de_esgotamento         =      models.FloatField(default=0)
    demonstracao_de_resultado_de_exaustao_de_amortizacao_de_deprec  =      models.FloatField(default=0)
    depreciacao_de_ativos_de_capital         =      models.FloatField(default=0)
    depreciacao_e_amortizacao_na_demonstracao_do_resultado   =      models.FloatField(default=0)
    depreciacao_reconciliada         =      models.FloatField(default=0)
    despesa_de_juros         =      models.FloatField(default=0)
    despesa_de_juros_nao_operacional         =      models.FloatField(default=0)
    despesa_de_receita_liquida_de_juros_nao_operacional      =      models.FloatField(default=0)
    despesa_operacional      =      models.FloatField(default=0)
    despesas_de_aluguel_suplementares        =      models.FloatField(default=0)
    despesas_de_vendas_e_marketing   =      models.FloatField(default=0)
    despesas_gerais_e_administrativas        =      models.FloatField(default=0)
    despesas_totais  =      models.FloatField(default=0)
    diluido_ni_availto_com_acionistas        =      models.FloatField(default=0)
    dividendos_de_acoes_preferenciais        =      models.FloatField(default=0)
    ebit     =      models.FloatField(default=0)
    ebitda   =      models.FloatField(default=0)
    ebitda_normalizado       =      models.FloatField(default=0)
    efeito_fiscal_de_itens_incomuns  =      models.FloatField(default=0)
    eliminar         =      models.FloatField(default=0)
    encargos_de_renda_especial       =      models.FloatField(default=0)
    lpa_basicos      =      models.FloatField(default=0)
    lpa_diluidos     =      models.FloatField(default=0)
    ganho_na_venda_de_ppe    =      models.FloatField(default=0)
    ganho_na_venda_de_titulos        =      models.FloatField(default=0)
    ganho_na_venda_do_negocio        =      models.FloatField(default=0)
    ganhos_de_participacao_acionaria         =      models.FloatField(default=0)
    ganhos_medios_de_diluicao        =      models.FloatField(default=0)
    impostos_especiais_de_consumo    =      models.FloatField(default=0)
    interesses_minoritarios  =      models.FloatField(default=0)
    itens_incomuns_totais    =      models.FloatField(default=0)
    lucro_bruto      =      models.FloatField(default=0)
    lucro_juros_capital_proprio_liquido_impostos     =      models.FloatField(default=0)
    lucro_liquido_acionistas_ordinarios      =      models.FloatField(default=0)
    lucro_liquido_da_operacao_continuada_particip_minoritaria_liq  =      models.FloatField(default=0)
    lucro_liquido_de_operacao_continua_e_descontinuada       =      models.FloatField(default=0)
    lucro_liquido_extraordinario     =      models.FloatField(default=0)
    lucro_liquido_incluindo_participacoes_nao_controladoras  =      models.FloatField(default=0)
    lucro_liquido_operacoes_continuas        =      models.FloatField(default=0)
    lucro_liquido_operacoes_descontinuas     =      models.FloatField(default=0)
    lucro_liquido_prejuizo_fiscal_compensar  =      models.FloatField(default=0)
    lucro_operacional        =      models.FloatField(default=0)
    outras_despesas_de_operacao      =      models.FloatField(default=0)
    outras_despesas_de_receita       =      models.FloatField(default=0)
    outras_despesas_de_receita_nao_operacional       =      models.FloatField(default=0)
    outro_dividendo_de_acoes_preferenciais   =      models.FloatField(default=0)
    outro_gand_um    =      models.FloatField(default=0)
    outros_custos_financeiros_totais         =      models.FloatField(default=0)
    outros_encargos_especiais        =      models.FloatField(default=0)
    outros_impostos  =      models.FloatField(default=0)
    pesquisa_e_desenvolvimento       =      models.FloatField(default=0)
    provisao_de_imposto      =      models.FloatField(default=0)
    provisao_para_devedores_duvidosos        =      models.FloatField(default=0)
    receita_de_juros_nao_operacional         =      models.FloatField(default=0)
    receita_liquida_de_juros         =      models.FloatField(default=0)
    receita_operacional      =      models.FloatField(default=0)
    receita_operacional_total_conforme_relatado      =      models.FloatField(default=0)
    reestruturacao_e_aquisicao_de_fusao      =      models.FloatField(default=0)
    renda_antes_de_impostos  =      models.FloatField(default=0)
    renda_antes_dos_impostos         =      models.FloatField(default=0)
    renda_normalizada        =      models.FloatField(default=0)
    rendimento_total         =      models.FloatField(default=0)
    rendimentos_de_juros     =      models.FloatField(default=0)
    resultado_liquido        =      models.FloatField(default=0)
    salarios_e_remuneracoes  =      models.FloatField(default=0)
    seguros_e_sinistros      =      models.FloatField(default=0)
    taxa_de_imposto_para_calculos    =      models.FloatField(default=0)
    taxas_de_aluguel_e_desembarque   =      models.FloatField(default=0)
    tipo_periodo     =      models.CharField(max_length=10,db_index=True)
    total_de_itens_incomuns_excluindo_fundo_de_comercio      =      models.FloatField(default=0)
    vendas_geral_e_administrativa    =      models.FloatField(default=0)

    class Meta:
        db_table = 'home_declaracao_renda'
        unique_together = [['acao', 'data', 'tipo_periodo','codigo_moeda']]
        ordering = ['acao', '-data']
        
class Financeiro(models.Model):  
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)     
    data = models.DateTimeField('data',default='2022-01-01',db_index=True)
    acao_emitida     =      models.FloatField(default=0)
    acao_ordinaria   =      models.FloatField(default=0)
    acoes_em_tesouraria      =      models.FloatField(default=0)
    acoes_medias_basicas     =      models.FloatField(default=0)
    acoes_medias_diluidas    =      models.FloatField(default=0)
    acoes_ordinarias         =      models.FloatField(default=0)
    acoes_preferenciais      =      models.FloatField(default=0)
    acoes_preferenciais_equidade    =      models.FloatField(default=0)
    ajustes_de_conversao_de_moeda_estrangeira        =      models.FloatField(default=0)
    alteracao_de_juros_a_pagar       =      models.FloatField(default=0)
    alteracao_do_imposto_a_pagar     =      models.FloatField(default=0)
    alteracao_do_imposto_de_renda_a_pagar    =      models.FloatField(default=0)
    alteracao_na_conta_a_pagar       =      models.FloatField(default=0)
    alteracao_na_despesa_acumulada   =      models.FloatField(default=0)
    alteracao_nas_contas_a_pagar_e_despesas_acumuladas       =      models.FloatField(default=0)
    alteracao_no_dividendo_a_pagar   =      models.FloatField(default=0)
    alteracao_no_pagamento   =      models.FloatField(default=0)
    alteracao_no_suplemento_em_dinheiro_conforme_relatado    =      models.FloatField(default=0)
    alteracoes_em_contas_a_receber   =      models.FloatField(default=0)
    amortizacao      =      models.FloatField(default=0)
    amortizacao_da_demonstracao_do_resultado_do_intangivel   =      models.FloatField(default=0)
    amortizacao_de_intangiveis       =      models.FloatField(default=0)
    amortizacao_de_titulos   =      models.FloatField(default=0)
    arrendamentos    =      models.FloatField(default=0)
    ativo_diferido_nao_circulante    =      models.FloatField(default=0)
    ativos_correntes         =      models.FloatField(default=0)
    ativos_de_impostos_diferidos_atuais      =      models.FloatField(default=0)
    ativos_de_impostos_diferidos_nao_correntes       =      models.FloatField(default=0)
    ativos_diferidos_atuais  =      models.FloatField(default=0)
    ativos_financeiros       =      models.FloatField(default=0)
    ativos_financeiros_designados_ao_valor_justo_pelo_result_total  =      models.FloatField(default=0)
    ativos_mantidos_para_venda_atuais        =      models.FloatField(default=0)
    ativos_pre_pagos         =      models.FloatField(default=0)
    ativos_pre_pagos_nao_circulantes         =      models.FloatField(default=0)
    ativos_tangiveis_liquidos        =      models.FloatField(default=0)
    ativos_totais    =      models.FloatField(default=0)
    beneficio_de_pensao_definido     =      models.FloatField(default=0)
    beneficios_do_empregado  =      models.FloatField(default=0)
    boa_vontade      =      models.FloatField(default=0)
    caixa_de_atividades_de_financiamento_descontinuadas      =      models.FloatField(default=0)
    caixa_de_atividades_de_investimento_descontinuadas       =      models.FloatField(default=0)
    caixa_de_atividades_operacionais_descontinuadas  =      models.FloatField(default=0)
    caixa_e_equivalentes_de_caixa    =      models.FloatField(default=0)
    capital_adicional_pago   =      models.FloatField(default=0)
    capital_de_giro  =      models.FloatField(default=0)
    capital_investido        =      models.FloatField(default=0)
    capital_social   =      models.FloatField(default=0)
    capital_total_parceria   =      models.FloatField(default=0)
    capitalizacao_total      =      models.FloatField(default=0)
    classes_de_pagamentos_em_dinheiro        =      models.FloatField(default=0)
    classes_de_recebimentos_de_caixa_de_atividades_operacionais      =      models.FloatField(default=0)
    cobertura_de_ativos_atuais       =      models.FloatField(default=0)
    codigo_moeda     =      models.CharField(max_length=60)
    compensacao_baseada_em_acoes     =      models.FloatField(default=0)
    compra_de_ppe    =      models.FloatField(default=0)
    compra_de_intangiveis    =      models.FloatField(default=0)
    compra_de_investimento   =      models.FloatField(default=0)
    compra_de_negocios       =      models.FloatField(default=0)
    compra_de_propriedades_de_investimento   =      models.FloatField(default=0)
    compra_e_venda_de_ppe_liquido    =      models.FloatField(default=0)
    compra_e_venda_de_intangiveis_liquidos   =      models.FloatField(default=0)
    compra_e_venda_de_investimento_liquido   =      models.FloatField(default=0)
    compra_e_venda_de_negocios_liquidos      =      models.FloatField(default=0)
    compra_e_venda_de_propriedades_de_investimento_liquido   =      models.FloatField(default=0)
    construcao_em_progresso  =      models.FloatField(default=0)
    construcoes_e_melhorias  =      models.FloatField(default=0)
    contas_a_pagar   =      models.FloatField(default=0)
    contas_a_pagar_comerciais_e_outras_nao_correntes         =      models.FloatField(default=0)
    contas_a_pagar_e_despesas_acumuladas     =      models.FloatField(default=0)
    contas_a_receber         =      models.DecimalField(max_digits=22,decimal_places=2,default=0)
    contas_a_receber_bruto   =      models.FloatField(default=0)
    contas_a_receber_nao_correntes   =      models.FloatField(default=0)
    custo_de_receita         =      models.FloatField(default=0)
    custo_reconciliado_da_receita    =      models.FloatField(default=0)
    dados_complementares_de_imposto_de_renda_pagos   =      models.FloatField(default=0)
    dados_complementares_de_juros_pagos      =      models.FloatField(default=0)    
    declaracao_de_renda_de_depreciacao       =      models.FloatField(default=0)
    declaracao_de_rendimentos_de_esgotamento         =      models.FloatField(default=0)
    demonstracao_de_resultado_de_exaustao_de_amortizacao_de_deprec  =      models.FloatField(default=0)
    depreciacao      =      models.FloatField(default=0)
    depreciacao_acumulada    =      models.FloatField(default=0)
    depreciacao_amortizacao_esgotamento      =      models.FloatField(default=0)
    depreciacao_de_ativos_de_capital         =      models.FloatField(default=0)
    depreciacao_e_amortizacao        =      models.FloatField(default=0)
    depreciacao_e_amortizacao_na_demonstracao_do_resultado   =      models.FloatField(default=0)
    depreciacao_reconciliada         =      models.FloatField(default=0)
    despesa_de_juros         =      models.FloatField(default=0)
    despesa_de_juros_nao_operacional         =      models.FloatField(default=0)
    despesa_de_receita_liquida_de_juros_nao_operacional      =      models.FloatField(default=0)
    despesa_operacional      =      models.FloatField(default=0)
    despesas_acumuladas_atuais       =      models.FloatField(default=0)
    despesas_acumuladas_nao_correntes        =      models.FloatField(default=0)
    despesas_com_pensoes_e_beneficios_a_empregados   =      models.FloatField(default=0)
    despesas_de_aluguel_suplementares        =      models.FloatField(default=0)
    despesas_de_capital      =      models.FloatField(default=0)
    despesas_de_capital_informadas   =      models.FloatField(default=0)
    despesas_de_vendas_e_marketing   =      models.FloatField(default=0)
    despesas_gerais_e_administrativas        =      models.FloatField(default=0)
    despesas_totais  =      models.FloatField(default=0)
    devido_a_partes_relacionadas_atuais      =      models.FloatField(default=0)
    devido_a_partes_relacionadas_nao_circulantes     =      models.FloatField(default=0)
    devido_de_partes_relacionadas_atuais     =      models.FloatField(default=0)
    diluido_ni_availto_com_acionistas        =      models.FloatField(default=0)
    dinheiro_financeiro      =      models.FloatField(default=0)
    dinheiro_restrito        =      models.FloatField(default=0)
    disposicoes_atuais       =      models.FloatField(default=0)
    disposicoes_de_longo_prazo       =      models.FloatField(default=0)
    divida_atual     =      models.FloatField(default=0)
    divida_atual_e_obrigacao_de_arrendamento_de_capital      =      models.FloatField(default=0)
    divida_de_longo_prazo    =      models.FloatField(default=0)
    divida_de_longo_prazo_e_obrigacao_de_arrendamento_de_capital     =      models.FloatField(default=0)
    divida_liquida   =      models.FloatField(default=0)
    divida_total     =      models.FloatField(default=0)
    dividas_de_partes_relacionadas_nao_circulantes   =      models.FloatField(default=0)
    dividendo_de_acoes_ordinarias_pago       =      models.FloatField(default=0)
    dividendo_pago_cfo       =      models.FloatField(default=0)
    dividendo_recebido_cfo   =      models.FloatField(default=0)
    dividendos_de_acoes_preferenciais        =      models.FloatField(default=0)
    dividendos_de_acoes_preferenciais_pagos  =      models.FloatField(default=0)
    dividendos_em_dinheiro_pagos     =      models.FloatField(default=0)
    dividendos_pagaveis      =      models.FloatField(default=0)
    dividendos_pagos_diretamente     =      models.FloatField(default=0)
    dividendos_recebidos_cfi         =      models.FloatField(default=0)
    dividendos_recebidos_direto      =      models.FloatField(default=0)
    ebit     =      models.FloatField(default=0)
    ebitda_normalizado       =      models.FloatField(default=0)
    efeito_das_alteracoes_cambiais   =      models.FloatField(default=0)
    efeito_fiscal_de_itens_incomuns  =      models.FloatField(default=0)
    eliminar         =      models.FloatField(default=0)
    emissao_de_acoes_ordinarias      =      models.FloatField(default=0)
    emissao_de_acoes_preferenciais   =      models.FloatField(default=0)
    emissao_de_capital_social        =      models.FloatField(default=0)
    emissao_de_divida        =      models.FloatField(default=0)
    emissao_de_divida_de_curto_prazo         =      models.FloatField(default=0)
    emissao_de_divida_de_longo_prazo         =      models.FloatField(default=0)
    emissao_liquida_de_acoes_ordinarias      =      models.FloatField(default=0)
    emissao_liquida_de_acoes_preferenciais   =      models.FloatField(default=0)
    emissao_liquida_de_divida_de_curto_prazo         =      models.FloatField(default=0)
    emissao_liquida_de_divida_de_longo_prazo         =      models.FloatField(default=0)
    emprestimos_a_receber    =      models.FloatField(default=0)
    encargos_de_renda_especial       =      models.FloatField(default=0)
    ppe_bruto        =      models.FloatField(default=0)
    ppe_liquido      =      models.FloatField(default=0)
    lpa_basicos      =      models.FloatField(default=0)
    lpa_diluidos     =      models.FloatField(default=0)
    equipamentos_de_moveis_de_maquinas       =      models.FloatField(default=0)
    equivalentes_de_caixa_e_investimentos_de_curto_prazo     =      models.FloatField(default=0)
    equivalentes_em_dinheiro         =      models.FloatField(default=0)
    fluxo_de_caixa_da_operação_descontinuada         =      models.FloatField(default=0)
    fluxo_de_caixa_das_atividades_de_financiamento_continuo  =      models.FloatField(default=0)
    fluxo_de_caixa_das_atividades_de_investimento_continuas  =      models.FloatField(default=0)
    fluxo_de_caixa_das_atividades_operacionais_continuas     =      models.FloatField(default=0)
    fluxo_de_caixa_de_amortizacao    =      models.FloatField(default=0)
    fluxo_de_caixa_de_financiamento  =      models.FloatField(default=0)
    fluxo_de_caixa_de_investimento   =      models.FloatField(default=0)
    fluxo_de_caixa_livre     =      models.FloatField(default=0)
    fluxo_de_caixa_operacional       =      models.FloatField(default=0)
    fluxos_de_caixa_de_uso_nas_atividades_operacionais_diretas       =      models.FloatField(default=0)
    fundo_de_comercio_e_outros_ativos_intangiveis    =      models.FloatField(default=0)
    ganho_na_venda_de_ppe    =      models.FloatField(default=0)
    ganho_na_venda_de_titulos        =      models.FloatField(default=0)
    ganho_na_venda_do_negocio        =      models.FloatField(default=0)
    ganho_perda_em_titulos_de_investimento   =      models.FloatField(default=0)
    ganho_perda_na_venda_do_negocio  =      models.FloatField(default=0)
    ganho_prejuizo_na_venda_de_ppe   =      models.FloatField(default=0)
    ganhos_de_participacao_acionaria         =      models.FloatField(default=0)
    ganhos_medios_de_diluicao        =      models.FloatField(default=0)
    ganhos_perdas_que_nao_afetam_os_lucros_acumulados        =      models.FloatField(default=0)
    imposto_de_renda_a_pagar         =      models.FloatField(default=0)
    imposto_de_renda_diferido        =      models.FloatField(default=0)
    imposto_diferido         =      models.FloatField(default=0)
    imposto_total_a_pagar    =      models.FloatField(default=0)
    impostos_a_receber       =      models.FloatField(default=0)
    impostos_especiais_de_consumo    =      models.FloatField(default=0)
    interesse_minoritario    =      models.FloatField(default=0)
    interesses_minoritarios  =      models.FloatField(default=0)
    inventario       =      models.FloatField(default=0)
    investimento_de_capital_de_longo_prazo   =      models.FloatField(default=0)
    investimento_em_ativos_financeiros       =      models.FloatField(default=0)
    investimento_em_joint_venture_sat_custo  =      models.FloatField(default=0)
    investimentos_e_adiantamentos    =      models.FloatField(default=0)
    investimentos_em_associados_a_custo      =      models.FloatField(default=0)
    investimentos_em_outros_empreendimentos_metodo_equiv_patrimoni  =      models.FloatField(default=0)
    investimentos_em_subsidiarias_a_custo    =      models.FloatField(default=0)
    itens_incomuns_totais    =      models.FloatField(default=0)
    juros_a_pagar    =      models.FloatField(default=0)
    juros_acumulados_a_receber       =      models.FloatField(default=0)
    juros_pagos_cff  =      models.FloatField(default=0)
    juros_pagos_cfo  =      models.FloatField(default=0)
    juros_pagos_direto       =      models.FloatField(default=0)
    juros_recebidos_cfi      =      models.FloatField(default=0)
    juros_recebidos_cfo      =      models.FloatField(default=0)
    juros_recebidos_direto   =      models.FloatField(default=0)
    linha_de_credito         =      models.FloatField(default=0)
    lucro_bruto      =      models.FloatField(default=0)
    lucro_juros_capital_proprio_liquido_impostos     =      models.FloatField(default=0)
    lucro_liquido_acionistas_ordinarios      =      models.FloatField(default=0)
    lucro_liquido_da_operacao_continuada_particip_minoritaria_liq  =      models.FloatField(default=0)
    lucro_liquido_de_operacao_continua_e_descontinuada       =      models.FloatField(default=0)
    lucro_liquido_de_operacoes_continuas     =      models.FloatField(default=0)
    lucro_liquido_extraordinario     =      models.FloatField(default=0)
    lucro_liquido_incluindo_participacoes_nao_controladoras  =      models.FloatField(default=0)
    lucro_liquido_operacoes_continuas        =      models.FloatField(default=0)
    lucro_liquido_operacoes_descontinuas     =      models.FloatField(default=0)
    lucro_liquido_prejuizo_fiscal_compensar  =      models.FloatField(default=0)
    lucro_operacional        =      models.FloatField(default=0)
    lucros_acumulados        =      models.FloatField(default=0)
    materias_primas  =      models.FloatField(default=0)
    mudanca_de_recebiveis    =      models.FloatField(default=0)
    mudanca_em_ativos_pre_pagos      =      models.FloatField(default=0)
    mudanca_em_outro_capital_de_giro         =      models.FloatField(default=0)
    mudanca_em_outros_ativos_circulantes     =      models.FloatField(default=0)
    mudanca_em_outros_passivos_circulantes   =      models.FloatField(default=0)
    mudanca_no_capital_de_giro       =      models.FloatField(default=0)
    mudanca_no_estoque       =      models.FloatField(default=0)
    mudancas_em_dinheiro     =      models.FloatField(default=0)
    notas_a_receber  =      models.FloatField(default=0)
    notas_atuais_a_pagar     =      models.FloatField(default=0)
    numero_de_acoes_em_tesouraria    =      models.FloatField(default=0)
    numero_de_acoes_ordinarias       =      models.FloatField(default=0)
    numero_de_acoes_preferenciais    =      models.FloatField(default=0)
    obrigacao_de_arrendamento_de_capital_atual       =      models.FloatField(default=0)
    obrigacao_de_arrendamento_de_capital_de_longo_prazo      =      models.FloatField(default=0)
    obrigacoes_de_arrendamento_de_capital    =      models.FloatField(default=0)
    outras_despesas_de_operacao      =      models.FloatField(default=0)
    outras_despesas_de_receita       =      models.FloatField(default=0)
    outras_despesas_de_receita_nao_operacional       =      models.FloatField(default=0)
    outras_mudancas_liquidas_de_investimento         =      models.FloatField(default=0)
    outras_participacoes_societarias         =      models.FloatField(default=0)
    outras_propriedades      =      models.FloatField(default=0)
    outro_ajuste_em_dinheiro_dentro_de_mudanca_em_dinheiro   =      models.FloatField(default=0)
    outro_ajuste_em_dinheiro_fora_da_mudanca_em_dinheiro     =      models.FloatField(default=0)
    outro_capital_social     =      models.FloatField(default=0)
    outro_dividendo_de_acoes_preferenciais   =      models.FloatField(default=0)
    outro_gand_um    =      models.FloatField(default=0)
    outros_a_pagar   =      models.FloatField(default=0)
    outros_ajustes_de_patrimonio     =      models.FloatField(default=0)
    outros_ativos_circulantes        =      models.FloatField(default=0)
    outros_ativos_intangiveis        =      models.FloatField(default=0)
    outros_ativos_nao_circulantes    =      models.FloatField(default=0)
    outros_creditos  =      models.FloatField(default=0)
    outros_custos_financeiros_totais         =      models.FloatField(default=0)
    outros_emprestimos_correntes     =      models.FloatField(default=0)
    outros_encargos_de_financiamento_liquidos        =      models.FloatField(default=0)
    outros_encargos_especiais        =      models.FloatField(default=0)
    outros_estoques  =      models.FloatField(default=0)
    outros_impostos  =      models.FloatField(default=0)
    outros_investimentos     =      models.FloatField(default=0)
    outros_investimentos_de_curto_prazo      =      models.FloatField(default=0)
    outros_itens_nao_monetarios      =      models.FloatField(default=0)
    outros_pagamentos_em_dinheiro_de_atividades_operacionais         =      models.FloatField(default=0)
    outros_passivos_circulantes      =      models.FloatField(default=0)
    outros_passivos_nao_circulantes  =      models.FloatField(default=0)
    outros_recebimentos_de_caixa_das_atividades_operacionais         =      models.FloatField(default=0)
    pagamentos_a_fornecedores_de_bens_e_servicos     =      models.FloatField(default=0)
    pagamentos_de_acoes_ordinarias   =      models.FloatField(default=0)
    pagamentos_de_acoes_preferenciais        =      models.FloatField(default=0)
    pagamentos_de_dividas_a_longo_prazo      =      models.FloatField(default=0)
    pagamentos_de_dividas_de_curto_prazo     =      models.FloatField(default=0)
    pagamentos_de_emissao_liquida_de_divida  =      models.FloatField(default=0)
    pagamentos_em_nome_dos_funcionarios      =      models.FloatField(default=0)
    pagaveis         =      models.FloatField(default=0)
    participacao_minoritaria_bruta_do_patrimonio_liquido_total       =      models.FloatField(default=0)
    passivo_circulante       =      models.FloatField(default=0)
    passivo_diferido_nao_circulante  =      models.FloatField(default=0)
    passivo_total_participacao_minoritaria_liquida   =      models.FloatField(default=0)
    passivos_de_impostos_diferidos_atuais    =      models.FloatField(default=0)
    passivos_de_impostos_diferidos_nao_correntes     =      models.FloatField(default=0)
    passivos_de_produtos_derivativos         =      models.FloatField(default=0)
    passivos_diferidos_atuais        =      models.FloatField(default=0)
    passivos_mantidos_para_venda_nao_circulantes     =      models.FloatField(default=0)
    patrimonio_liquido       =      models.FloatField(default=0)
    perda_de_ganho_nao_realizado     =      models.FloatField(default=0)
    perda_de_ganho_nao_realizado_em_titulos_de_investimento  =      models.FloatField(default=0)
    perda_liquida_de_ganhos_cambiais_em_moeda_estrangeira    =      models.FloatField(default=0)
    perdas_de_ganhos_operacionais    =      models.FloatField(default=0)
    perdas_de_lucros_de_investimentos_de_capital     =      models.FloatField(default=0)
    pesquisa_e_desenvolvimento       =      models.FloatField(default=0)
    planos_de_pensao_nao_correntes_e_outros_planos_benef_pos_aposen  =      models.FloatField(default=0)
    posicao_de_caixa_inicial         =      models.FloatField(default=0)
    posicao_final_de_caixa   =      models.FloatField(default=0)
    previdencia_e_outros_planos_de_benef_pos_aposent_atuais  =      models.FloatField(default=0)
    produto_da_opcao_de_compra_de_acoes_exercida     =      models.FloatField(default=0)
    produtos_acabados        =      models.FloatField(default=0)
    propriedades     =      models.FloatField(default=0)
    propriedades_de_investimento     =      models.FloatField(default=0)
    provisao_de_imposto      =      models.FloatField(default=0)
    provisao_e_baixa_de_ativos       =      models.FloatField(default=0)
    provisao_para_devedores_duvidosos        =      models.FloatField(default=0)
    provisoes_para_ajustes_de_estoques       =      models.FloatField(default=0)
    provisoes_para_ajustes_de_recebiveis     =      models.FloatField(default=0)
    provisao_para_contas_duvidosos =      models.FloatField(default=0)
    recebiveis        =      models.FloatField(default=0)
    recebiveis_de_notas_nao_correntes        =      models.FloatField(default=0)
    receita_de_juros_nao_operacional         =      models.FloatField(default=0)
    receitas_de_subvencoes_governamentais   =      models.FloatField(default=0)
    receita_diferida_atual   =      models.FloatField(default=0)
    receita_diferida_nao_corrente    =      models.FloatField(default=0)
    receita_liquida_de_juros         =      models.FloatField(default=0)
    receita_operacional      =      models.FloatField(default=0)
    receita_operacional_total_conforme_relatado      =      models.FloatField(default=0)
    recibos_de_clientes      =      models.FloatField(default=0)
    recompra_de_capital      =      models.FloatField(default=0)
    reembolso_de_divida      =      models.FloatField(default=0)
    reembolso_de_impostos_pago_direto        =      models.FloatField(default=0)
    reembolso_de_impostos_pagos      =      models.FloatField(default=0)
    reestruturacao_e_aquisicao_de_fusao      =      models.FloatField(default=0)
    renda_antes_de_impostos  =      models.FloatField(default=0)
    renda_antes_dos_impostos         =      models.FloatField(default=0)
    renda_normalizada        =      models.FloatField(default=0)
    rendimento_total         =      models.FloatField(default=0)
    rendimentos_de_juros     =      models.FloatField(default=0)
    reserva_de_reavaliacao_de_ativos_fixos   =      models.FloatField(default=0)
    responsabilidades_minimas_de_pensao      =      models.FloatField(default=0)
    resultado_liquido        =      models.FloatField(default=0)
    salarios_e_remuneracoes  =      models.FloatField(default=0)
    seguros_e_sinistros      =      models.FloatField(default=0)
    taxa_de_desvalorizacao_de_ativos         =      models.FloatField(default=0)
    taxa_de_imposto_para_calculos    =      models.FloatField(default=0)
    taxas_de_aluguel_e_desembarque   =      models.FloatField(default=0)
    terrenos_e_benfeitorias  =      models.FloatField(default=0)
    tipo_periodo     =      models.CharField(max_length=10,db_index=True)
    titulos_amortizados   =      models.FloatField(default=0)
    titulos_disponiveis_para_venda   =      models.FloatField(default=0)
    titulos_mantidos_ate_o_vencimento        =      models.FloatField(default=0)
    titulos_para_negociacao  =      models.FloatField(default=0)
    titulos_preferenciais_fora_do_patrimonio_liquido         =      models.FloatField(default=0)
    total_de_ativos_nao_circulantes  =      models.FloatField(default=0)
    total_de_itens_incomuns_excluindo_fundo_de_comercio      =      models.FloatField(default=0)
    total_do_passivo_nao_circulante_participacao_minoritaria_liq  =      models.FloatField(default=0)
    trabalho_em_andamento    =      models.FloatField(default=0)
    valor_contabil_tangivel  =      models.FloatField(default=0)
    venda_de_ep      =      models.FloatField(default=0)
    venda_de_intangiveis     =      models.FloatField(default=0)
    venda_de_investimento    =      models.FloatField(default=0)
    venda_de_negocios        =      models.FloatField(default=0)
    venda_de_propriedades_de_investimento    =      models.FloatField(default=0)
    vendas_domesticas        =      models.FloatField(default=0)
    vendas_externas  =      models.FloatField(default=0)
    vendas_geral_e_administrativa    =      models.FloatField(default=0)

    class Meta:
        unique_together = [['acao', 'data', 'tipo_periodo','codigo_moeda']]
        ordering = ['acao', '-data']
        
class FluxoCaixa(models.Model):  
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)         
    data = models.DateTimeField('data',default='2022-01-01',db_index=True)
    alteracao_de_juros_a_pagar       =      models.FloatField(default=0)
    alteracao_do_imposto_a_pagar     =      models.FloatField(default=0)
    alteracao_do_imposto_de_renda_a_pagar    =      models.FloatField(default=0)
    alteracao_na_conta_a_pagar       =      models.FloatField(default=0)
    alteracao_na_despesa_acumulada   =      models.FloatField(default=0)
    alteracao_nas_contas_a_pagar_e_despesas_acumuladas       =      models.FloatField(default=0)
    alteracao_no_dividendo_a_pagar   =      models.FloatField(default=0)
    alteracao_no_pagamento   =      models.FloatField(default=0)
    alteracao_no_suplemento_em_dinheiro_conforme_relatado    =      models.FloatField(default=0)
    alteracoes_em_contas_a_receber   =      models.FloatField(default=0)
    amortizacao_de_intangiveis       =      models.FloatField(default=0)
    amortizacao_de_titulos   =      models.FloatField(default=0)
    caixa_de_atividades_de_financiamento_descontinuadas      =      models.FloatField(default=0)
    caixa_de_atividades_de_investimento_descontinuadas       =      models.FloatField(default=0)
    caixa_de_atividades_operacionais_descontinuadas  =      models.FloatField(default=0)
    classes_de_pagamentos_em_dinheiro        =      models.FloatField(default=0)
    classes_de_recebimentos_de_caixa_de_atividades_operacionais      =      models.FloatField(default=0)
    codigo_moeda     =      models.CharField(max_length=60)
    compensacao_baseada_em_acoes     =      models.FloatField(default=0)
    compra_de_ppe    =      models.FloatField(default=0)
    compra_de_intangiveis    =      models.FloatField(default=0)
    compra_de_investimento   =      models.FloatField(default=0)
    compra_de_negocios       =      models.FloatField(default=0)
    compra_de_propriedades_de_investimento   =      models.FloatField(default=0)
    compra_e_venda_de_ppe_liquido    =      models.FloatField(default=0)
    compra_e_venda_de_intangiveis_liquidos   =      models.FloatField(default=0)
    compra_e_venda_de_investimento_liquido   =      models.FloatField(default=0)
    compra_e_venda_de_negocios_liquidos      =      models.FloatField(default=0)
    compra_e_venda_de_propriedades_de_investimento_liquido   =      models.FloatField(default=0)
    dados_complementares_de_imposto_de_renda_pagos   =      models.FloatField(default=0)
    dados_complementares_de_juros_pagos      =      models.FloatField(default=0)
    depreciacao      =      models.FloatField(default=0)
    depreciacao_amortizacao_esgotamento      =      models.FloatField(default=0)
    depreciacao_e_amortizacao        =      models.FloatField(default=0)
    despesas_com_pensoes_e_beneficios_a_empregados   =      models.FloatField(default=0)
    despesas_de_capital      =      models.FloatField(default=0)
    despesas_de_capital_informadas   =      models.FloatField(default=0)
    dividendo_de_acoes_ordinarias_pago       =      models.FloatField(default=0)
    dividendo_pago_cfo       =      models.FloatField(default=0)
    dividendo_recebido_cfo   =      models.FloatField(default=0)
    dividendos_de_acoes_preferenciais_pagos  =      models.FloatField(default=0)
    dividendos_em_dinheiro_pagos     =      models.FloatField(default=0)
    dividendos_pagos_diretamente     =      models.FloatField(default=0)
    dividendos_recebidos_cfi         =      models.FloatField(default=0)
    dividendos_recebidos_direto      =      models.FloatField(default=0)
    efeito_das_alteracoes_cambiais   =      models.FloatField(default=0)
    emissao_de_acoes_ordinarias      =      models.FloatField(default=0)
    emissao_de_acoes_preferenciais   =      models.FloatField(default=0)
    emissao_de_capital_social        =      models.FloatField(default=0)
    emissao_de_divida        =      models.FloatField(default=0)
    emissao_de_divida_de_curto_prazo         =      models.FloatField(default=0)
    emissao_de_divida_de_longo_prazo         =      models.FloatField(default=0)
    emissao_liquida_de_acoes_ordinarias      =      models.FloatField(default=0)
    emissao_liquida_de_acoes_preferenciais   =      models.FloatField(default=0)
    emissao_liquida_de_divida_de_curto_prazo         =      models.FloatField(default=0)
    emissao_liquida_de_divida_de_longo_prazo         =      models.FloatField(default=0)
    esgotamento         =      models.FloatField(default=0)
    fluxo_de_caixa_da_operacao_descontinuada         =      models.FloatField(default=0)
    fluxo_de_caixa_das_atividades_de_financiamento_continuo  =      models.FloatField(default=0)
    fluxo_de_caixa_das_atividades_de_investimento_continuas  =      models.FloatField(default=0)
    fluxo_de_caixa_das_atividades_operacionais_continuas     =      models.FloatField(default=0)
    fluxo_de_caixa_de_amortizacao    =      models.FloatField(default=0)
    fluxo_de_caixa_de_financiamento  =      models.FloatField(default=0)
    fluxo_de_caixa_de_investimento   =      models.FloatField(default=0)
    fluxo_de_caixa_livre     =      models.FloatField(default=0)
    fluxo_de_caixa_operacional       =      models.FloatField(default=0)
    fluxos_de_caixa_de_uso_nas_atividades_operacionais_diretas       =      models.FloatField(default=0)
    ganho_perda_em_titulos_de_investimento   =      models.FloatField(default=0)
    ganho_perda_na_venda_do_negocio  =      models.FloatField(default=0)
    ganho_prejuizo_na_venda_de_ppe   =      models.FloatField(default=0)
    imposto_de_renda_diferido        =      models.FloatField(default=0)
    imposto_diferido         =      models.FloatField(default=0)
    juros_pagos_cff  =      models.FloatField(default=0)
    juros_pagos_cfo  =      models.FloatField(default=0)
    juros_pagos_direto       =      models.FloatField(default=0)
    juros_recebidos_cfi      =      models.FloatField(default=0)
    juros_recebidos_cfo      =      models.FloatField(default=0)
    juros_recebidos_direto   =      models.FloatField(default=0)
    lucro_liquido_de_operacoes_continuas     =      models.FloatField(default=0)
    mudanca_de_recebiveis    =      models.FloatField(default=0)
    mudanca_em_ativos_pre_pagos      =      models.FloatField(default=0)
    mudanca_em_outro_capital_de_giro         =      models.FloatField(default=0)
    mudanca_em_outros_ativos_circulantes     =      models.FloatField(default=0)
    mudanca_em_outros_passivos_circulantes   =      models.FloatField(default=0)
    mudanca_no_capital_de_giro       =      models.FloatField(default=0)
    mudanca_no_estoque       =      models.FloatField(default=0)
    mudancas_em_dinheiro     =      models.FloatField(default=0)
    outras_mudancas_liquidas_de_investimento         =      models.FloatField(default=0)
    outro_ajuste_em_dinheiro_dentro_de_mudanca_em_dinheiro   =      models.FloatField(default=0)
    outro_ajuste_em_dinheiro_fora_da_mudanca_em_dinheiro     =      models.FloatField(default=0)
    outros_encargos_de_financiamento_liquidos        =      models.FloatField(default=0)
    outros_itens_nao_monetarios      =      models.FloatField(default=0)
    outros_pagamentos_em_dinheiro_de_atividades_operacionais         =      models.FloatField(default=0)
    outros_recebimentos_de_caixa_das_atividades_operacionais         =      models.FloatField(default=0)
    pagamentos_a_fornecedores_de_bens_e_servicos     =      models.FloatField(default=0)
    pagamentos_de_acoes_ordinarias   =      models.FloatField(default=0)
    pagamentos_de_acoes_preferenciais        =      models.FloatField(default=0)
    pagamentos_de_dividas_a_longo_prazo      =      models.FloatField(default=0)
    pagamentos_de_dividas_de_curto_prazo     =      models.FloatField(default=0)
    pagamentos_de_emissao_liquida_de_divida  =      models.FloatField(default=0)
    pagamentos_em_nome_dos_funcionarios      =      models.FloatField(default=0)
    perda_de_ganho_nao_realizado_em_titulos_de_investimento  =      models.FloatField(default=0)
    perda_liquida_de_ganhos_cambiais_em_moeda_estrangeira    =      models.FloatField(default=0)
    perdas_de_ganhos_operacionais    =      models.FloatField(default=0)
    perdas_de_lucros_de_investimentos_de_capital     =      models.FloatField(default=0)
    posicao_de_caixa_inicial         =      models.FloatField(default=0)
    posicao_final_de_caixa   =      models.FloatField(default=0)
    produto_da_opcao_de_compra_de_acoes_exercida     =      models.FloatField(default=0)
    provisao_e_baixa_de_ativos       =      models.FloatField(default=0)
    receitas_de_subvencoes_governamentais   =      models.FloatField(default=0)
    recibos_de_clientes      =      models.FloatField(default=0)
    recompra_de_capital      =      models.FloatField(default=0)
    reembolso_de_divida      =      models.FloatField(default=0)
    reembolso_de_impostos_pago_direto        =      models.FloatField(default=0)
    reembolso_de_impostos_pagos      =      models.FloatField(default=0)
    resultado_liquido        =      models.FloatField(default=0)
    taxa_de_desvalorizacao_de_ativos         =      models.FloatField(default=0)
    tipo_periodo     =      models.CharField(max_length=10,db_index=True)
    venda_de_ep      =      models.FloatField(default=0)
    venda_de_intangiveis     =      models.FloatField(default=0)
    venda_de_investimento    =      models.FloatField(default=0)
    venda_de_negocios        =      models.FloatField(default=0)
    venda_de_propriedades_de_investimento    =      models.FloatField(default=0)
    vendas_domesticas        =      models.FloatField(default=0)
    vendas_externas  =      models.FloatField(default=0)

    class Meta:
        db_table = 'home_fluxo_caixa'
        unique_together = [['acao', 'data', 'tipo_periodo','codigo_moeda']]
        ordering = ['acao', '-data']

class MetricaAvaliacao(models.Model):      
    acao = models.ForeignKey("Acao", on_delete=models.CASCADE,db_index=True)         
    data = models.DateTimeField('data',default='2022-01-01',db_index=True)
    razao_preco_lucro        =      models.FloatField(default=0)
    razao_preco_lucro_crescimento    =      models.FloatField(default=0)
    razao_preco_lucro_futuro         =      models.FloatField(default=0)
    razao_preco_valor_contabil       =      models.FloatField(default=0)
    razao_preco_venda        =      models.FloatField(default=0)
    razao_valor_da_empresa_ebitda    =      models.FloatField(default=0)
    razao_valor_da_empresas_ebitda   =      models.FloatField(default=0)
    razao_valor_da_empresas_receita  =      models.FloatField(default=0)
    tipo_periodo     =      models.CharField(max_length=10,db_index=True)
    valor_da_empresa         =      models.FloatField(default=0)
    valor_de_mercado         =      models.FloatField(default=0)

    class Meta:
        db_table = 'home_metrica_avaliacao'
        unique_together = [['acao', 'data']]
        ordering = ['acao', '-data']

def subsituiMaiusculaPorUnderlineTraduz(translator, txt):
    # ic = "".join(i if i.islower() else '_' + i.lower() if i != '_' else '' for i in txt) #[1:]
    ic = "".join(i if i.islower() else '_' + i.lower() for i in txt) #[1:]
    ic = "".join(i if len(i) <= 1 else '_' + i + '_' for i in ic.rsplit('_')).replace('__', '_')
    if ic[0] == '_': ic = ic[1::]
    if ic[len(ic)-1] == '_': ic = ic[:-1:]
    ic = translator.translate(ic.replace('_', ' '), dest='pt').text
    intab = " -áÁãÃâÂàÀéÉêÊíÍóÓôÔõÕúÚçÇ"
    outab = "__aAaAaAaAeEeEiIoOoOoOuUcC"
    ic = ic.translate(''.maketrans(intab, outab)).lower()
    return ic

def ajustarNumero(df):
    for it in df.columns:
        if df[it].dtype.name != 'datetime64[ns]':
            try:
                df[it] = pd.to_numeric(df[it])
            except Exception as exceptionObj:
                erro = exceptionObj.args[0]
                # print(exceptionObj.args[0])
    return df    

def ajustarData(df, indexRegistros):
    incluirData = True
    for col in df.columns: 
        if col in indexRegistros and ('data' in col.lower() or 'date' in col.lower()):
            try:
                df[col] = pd.to_datetime(df[col],utc=True,infer_datetime_format=True)
            except:
                df[col] = date.today()
            incluirData = False
        for idx, it in df.iterrows():
            if type(it[col]) is dict:
                if col in indexRegistros: df.drop(idx, inplace=True) 
                else: df.loc[idx,col] = None #date.today()
            elif ('data' in col.lower() or 'date' in col.lower()) and it[col] == '':
                df.loc[idx,col] = None 
    if incluirData: df['data'] = pd.to_datetime(date.today(),utc=True,infer_datetime_format=True) 
    
    return df
    
def normalizeDict(d, prefixo=''):
    df = pd.json_normalize(d, sep='_')
    if prefixo != '': 
        for it in df.columns:
            df.rename(columns={it : prefixo+it},inplace=True)
    for it in df.columns:
        if type(df[it][0]) is list and len(df[it][0]) > 0:
            if type(df[it][0][0]) is dict:
                df1 = normalizeDict(df[it][0][0],prefixo=it+'_')
                df.drop(it, axis=1, inplace=True)
                df = df.merge(df1, left_index=True, right_index=True)
    return df

def ajustaCamposDict(df,intraDia):
    for it in df.columns:
        if 'date' in it.lower():
            for index, item in df.iterrows():
                if not (pd.isna(item[it]) or str(item[it]).isnumeric() or type(item[it]) is float or item[it] is None):
                    if len(item[it]) > 0:
                        if type(item[it][0]) is str:
                            dt_aux = item[it][0]
                        elif type(item[it][0]) is list:
                            dt_aux = item[it][0][0]
                        if not (dt_aux[-1:] is int):
                            if len(dt_aux[:-2]) >= 10: df.loc[index,it] = pd.to_datetime(dt_aux[:-2],utc=True,infer_datetime_format=True) if intraDia else pd.to_datetime(dt_aux[:-2],infer_datetime_format=True)
                        else:
                            if len(dt_aux) >= 10: df.loc[index,it] = pd.to_datetime(dt_aux,utc=True,infer_datetime_format=True) if intraDia else pd.to_datetime(dt_aux,infer_datetime_format=True)
                    else:
                        df.loc[index,it] = None
        df.rename(columns={it : '_'.join(it.split('_')[1:])}, inplace=True)

    return df

def remove_outlier(df_in, col_name, perc_inferior=0.2, perc_superior=0.8):
    q1 = df_in[col_name].quantile(perc_inferior)
    q3 = df_in[col_name].quantile(perc_superior)
    iqr = q3-q1 #Interquartile range
    fence_low  = q1-1.5*iqr
    fence_high = q3+1.5*iqr
    df_out = df_in.loc[(df_in[col_name] > fence_low) & (df_in[col_name] < fence_high)]
    return df_out

class Ranking(models.Model):
    nome = models.CharField(max_length=40, unique=True)    
    ordem = models.IntegerField(default=0)
    ajuda = models.CharField(max_length=100,default='')    
    ascendente = models.BooleanField(default=True)
    visivel = models.BooleanField(default=True)
    modelo = models.CharField(max_length=100,default='')
    propriedade = models.CharField(max_length=100,default='')
    parametro = models.CharField(max_length=100,default='')

    class Meta:
        db_table = 'home_ranking'
        ordering = ['ordem']

    def rankear(self, projecao):
        self.rankeamento_set.filter(projecao_acao__projecao=projecao).delete()
        df = pd.DataFrame()
        for projecaoAcao in projecao.projecaoacao_set.filter(acao__empresa__cod_cvm__gt=0):            
            # Utiliza o objeto e método cadastrados na tabela Ranking para calcular o índice se o índice retornar None adiciona no Rankeamento com nota 0, caso contrário rankeia
            objeto = 'projecaoAcao.'+ self.modelo if len(self.modelo) > 0 else 'projecaoAcao'
            indice = getattr(eval(objeto), self.propriedade)(eval(self.parametro)) if self.parametro != '' else getattr(eval(objeto), self.propriedade)
            if indice: df = pd.concat([df, pd.DataFrame({'indice':[indice], 'projecao_acao_id':[projecaoAcao.id]})])
            else: Rankeamento(projecaoacao=projecaoAcao, ranking=self).save()
        df['indice_rank'] = df.indice.rank(pct=True,method='first', ascending=self.ascendente) * 15
        df['ranking_id'] = self.id
        Rankeamento.objects.bulk_create([Rankeamento(**criaInstanciaModelo(Rankeamento,linha,df.columns)) for idx_ii,linha in df.iterrows()])

class Rankeamento(models.Model):
    ranking = models.ForeignKey(Ranking, on_delete=models.CASCADE,db_index=True)
    projecaoacao = models.ForeignKey(ProjecaoAcao, on_delete=models.CASCADE,db_index=True)
    indice = models.FloatField(default=0)
    indice_rank = models.FloatField(default=0)
    media = models.FloatField(default=0)
    desvio_padrao =  models.FloatField(default=0)
    tendencia =  models.FloatField(default=0)
    media_ponderada = models.FloatField(default=0)

    class Meta:
        unique_together = [['projecaoacao', 'ranking']]
        # ordering = ['-ranking', 'projecaoacao']
        ordering = ['-indice_rank']

    @property
    def nota(self):
        notas = ['E -','E -','E','E +','D -','D','D +','C -','C','C +','B -','B','B +','A -','A','A +']
        r = notas[int(round(self.indice_rank,0))] if not isnan(self.indice_rank) else notas[0]
        return r

class Acao(models.Model):
    codigo = models.CharField(max_length=14,db_index=True, unique=True)
    codigo_br = models.CharField(max_length=14,db_index=True, unique=True, default='')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE,db_index=True)
    codigos = models.CharField(max_length=100,default='[]')
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['codigo']
        
    # @property
    # def codigo_br(self):
    #     return str(self.codigo).split('.')[0].upper()

    @property
    def estabilidade(self):
        indice = None
        dataInicial = pd.to_datetime(datetime.today() - timedelta(days=365),utc=True,infer_datetime_format=True)
        cotacoes = pd.DataFrame(self.cotacao_set.filter(data__gte=dataInicial).values('fechamento'))
        if not cotacoes.empty:
            indice = cotacoes.fechamento.ewm(alpha=0.2).std().iloc[-1]
            if (indice / cotacoes.fechamento.iloc[-1])>0.2 or indice==0: indice = None
        return indice

    @property
    def dividendos(self):
        dataInicial = pd.to_datetime(datetime.today() - timedelta(days=365*10),utc=True,infer_datetime_format=True)
        indice = None
        df = pd.DataFrame(self.cotacao_set.filter(Q(data__gte=dataInicial) & Q(dividendos__gt=0)).alias(perc_div=F('dividendos')/F('fechamento')*100).values('data__year').annotate(Sum('perc_div')))
        if not df.empty:
            dfn = pd.DataFrame({'perc_div__sum': np.zeros(date.today().year-dataInicial.year+1)},index=range(dataInicial.year, date.today().year+1))
            df.set_index('data__year',inplace=True)
            df = pd.concat([df,dfn.loc[dfn.index.difference(df.index)]]).sort_index()
            indice1 = df.perc_div__sum.ewm(alpha=0.5).mean().iloc[-1] 
            indice = df.perc_div__sum.ewm(alpha=0.5).mean().iloc[-1] / df.perc_div__sum.ewm(alpha=0.5).std().iloc[-1]
            if not (0 < indice <= 30): indice = None
        return indice

    @property
    # Menor é melhor Ranking configurado como descendente
    def preco(self):
        dataInicial = pd.to_datetime(datetime.today() - timedelta(days=365*5),utc=True,infer_datetime_format=True)
        indice = None
        dfR = pd.DataFrame(self.empresa.cvmresultado_set.filter(tipo_periodo=self.empresa.tipo_periodo).values('data_fim_exercicio','escala_moeda','resultado_antes_tributos_sobre_lucro','resultado_antes_resultado_financeiro_tributos','lucro_prejuizo_consolidado_periodo','resultado_liquido_operacoes_continuadas').order_by('-data_fim_exercicio')) 
        #dfR = dfR.apply(ajustaEscalaTabelaCVM,axis=1)
        # Agrupa o resultado em 4 trimestres para compatibilizar com os resultados anuais / sazonais
        if self.empresa.tipo_periodo == '3M':
            for coluna in ['resultado_antes_tributos_sobre_lucro','resultado_antes_resultado_financeiro_tributos','lucro_prejuizo_consolidado_periodo','resultado_liquido_operacoes_continuadas']:
                dfR[coluna] = [dfR[coluna].iloc[idx:idx+4:].sum() for idx in dfR.index]
            dfR = dfR[-4::-1]
        dfC = pd.DataFrame(self.empresa.cvmcomposicaocapital_set.values('data_fim_exercicio','on_mercado','pn_mercado'))
        df = pd.DataFrame(self.cotacao_set.filter(data__gte=dataInicial).values('data','fechamento'))
        if not dfR.empty and not dfC.empty and not df.empty: 
            dfR['lucro'] = dfR.lucro_prejuizo_consolidado_periodo if dfR.lucro_prejuizo_consolidado_periodo.sum() > dfR.resultado_liquido_operacoes_continuadas.sum() else dfR.resultado_liquido_operacoes_continuadas
            dfR['ebitda'] = dfR.resultado_antes_tributos_sobre_lucro if dfR.resultado_antes_tributos_sobre_lucro.sum() > dfR.resultado_antes_resultado_financeiro_tributos.sum() else dfR.resultado_antes_resultado_financeiro_tributos
            dfR = dfR.rename(columns={'data_fim_exercicio':'data'})
            dfR = dfR.merge(dfC.rename(columns={'data_fim_exercicio':'data'}), how='inner', left_on='data', right_on='data').sort_values('data')
            df = df.merge(dfR, how='outer', left_on='data', right_on='data').sort_values('data').ffill().dropna().reset_index(drop=True)            
            df['preco_lucro'] = df.fechamento / (df.lucro / (df.on_mercado + df.pn_mercado)) 
            df['media_lucro'] = df.preco_lucro.ewm(alpha=0.5).mean()
            df['preco_ebitda'] = df.fechamento / (df.ebitda / (df.on_mercado + df.pn_mercado))
            df['media_ebitda'] = df.preco_ebitda.ewm(alpha=0.5).mean()
            if df.preco_lucro.iloc[-1] > 0 and df.media_lucro.iloc[-1] > 0:
                indice = df.preco_lucro.iloc[-1] / df.media_lucro.iloc[-1]
            elif df.preco_ebitda.iloc[-1] > 0 and df.media_ebitda.iloc[-1] > 0:
                indice = df.preco_ebitda.iloc[-1] / df.media_ebitda.iloc[-1]
        return indice

    def importarDados(self):      
        for codigoAcao in eval(self.codigos):  
            print('Verificando', codigoAcao)    
            parametros = pd.DataFrame(ParametroImportacao.objects.filter(Q(biblioteca='yq') & Q(atualizar=True)).values())
            dfErrosDic = pd.DataFrame()
            ticker = False
            for idxTab, p in parametros.iterrows():
                nome_modelo = p.modelo if len(p.sufixo) == 0 else p.modelo[:-len(p.sufixo)]
                modelo = apps.get_model('home', nome_modelo)
                
                indexRegistros, importadosRename, periodoAtualizacao = eval(p.index_registros), eval(p.importados_rename), int(p.periodo_atualizacao)
                print('Verificando', p.metodo_ticker, codigoAcao)    
                atualizarResultado, repetir, repeticoes, resultado = False, True, 0, 'sem dados'                     
                periodo = pd.to_datetime(datetime.now() - timedelta(days=periodoAtualizacao),utc=True,infer_datetime_format=True)
                resultadoGravado = pd.DataFrame(self.resultadoimportacao_set.filter(Q(modelo=p.modelo) & Q(data__gt=periodo)).order_by('-data').values())
                if len(resultadoGravado) > 0:
                    repetir = not ('atualizado' in list(resultadoGravado['resultado']) or 'sem dados' in list(resultadoGravado['resultado']))
                    resultado = resultadoGravado['resultado'][0]
                    if 'No data available' in resultado or "None of ['date'] are in the columns" in resultado: 
                        resultado, repetir = 'sem dados', False
                while repetir and repeticoes <= 2:
                    repetir = False
                    try:
                        if not ticker:
                            ticker = Ticker(codigoAcao, #username='ricardo.malvessi@yahoo.com', password='F1nanca$1970', country='brazil', timeout=3000, 
                                    )            
                        if callable(getattr(Ticker, p.metodo_ticker)):
                            if pd.isna(p.parametro_ticker1):
                                importados = getattr(ticker,p.metodo_ticker)()
                            elif pd.isna(p.parametro_ticker2):
                                importados = getattr(ticker,p.metodo_ticker)(p.parametro_ticker1) 
                            elif pd.isna(p.parametro_ticker3):
                                p1 = p.parametro_ticker1
                                if nome_modelo == 'Cotacao': 
                                    dtMin = self.cotacao_set.aggregate(Min('data'))['data__min']
                                    if dtMin: 
                                        if dtMin.date() > (datetime.today() - timedelta(days=60)).date(): 
                                            p1 = 'max'
                                importados = getattr(ticker,p.metodo_ticker)(p1,p.parametro_ticker2) 
                            else:
                                importados = getattr(ticker,p.metodo_ticker)(p.parametro_ticker1, p.parametro_ticker2,p.parametro_ticker3) 
                        else:
                            importados = getattr(ticker,p.metodo_ticker)
                    except Exception as inst:                            
                        if len(inst.args)>0: 
                            estado = inst.args[0]
                        elif type(inst) == urllib.error.HTTPError: 
                            estado = inst.msg
                        imprimir= True
                        if (p.intra_dia or periodoAtualizacao <= 1) and type(estado) is str:
                            imprimir = not 'No data available' in estado
                        if imprimir:
                            print(f'Erro ao ler as informações referentes a tabela {p.modelo} da ação {codigoAcao}', estado)
                        resultado = estado
                        importados = pd.DataFrame()
                    if type(importados) is dict: 
                        if len(importados) > 0:
                            if codigoAcao in importados:
                                if type(importados[codigoAcao]) is str:
                                    repetir = ('TIMEOUT' in importados[codigoAcao].upper()) or ('WAITED' in importados[codigoAcao].upper())
                                    if not (('DATA' in importados[codigoAcao].upper()) or ('QUOTE' in importados[codigoAcao].upper())):
                                        if 'User is not logged in' in importados[codigoAcao]:
                                            repetir = True      
                                            del ticker
                                            ticker = Ticker(codigoAcao, #username='ricardo.malvessi@yahoo.com', password='F1nanca$1970', country='brazil', timeout=3000, 
                                                            )            
                                        print(importados)
                                else:
                                    # importados = normalizeDict(importados)    
                                    # importados = ajustaCamposDict(importados, p.intra_dia)
                                    # importados['codigo'] = codigoAcao
                                    importados = pd.DataFrame()
                                    resultado, repetir = 'sem dados', False
                            elif 'error' in importados:
                                print(importados)
                                repetir = True      
                                repeticoes += 1
                    if type(importados) is pd.DataFrame and len(importados) > 0:
                        if p.transpor: importados = importados.transpose()
                        importados.reset_index(inplace=True)  
                        if importadosRename != '': importados.rename(columns=importadosRename, inplace=True)
                        if 'symbol' in importados.columns and not 'codigo' in importados.columns: importados.rename(columns={'symbol' : 'codigo'}, inplace=True)
                        if not 'acao_id' in importados.columns: importados['acao_id'] = self.pk
                        if importadosRename != '': importados.rename(columns=importadosRename, inplace=True)                            
                        importados = ajustarData(importados, indexRegistros)
                        importados = importados[importados.data.dt.second == 0] if p.intra_dia else importados[importados.data.dt.time == time(0,0,0)]
                        if p.hora_liberado > time(datetime.now().hour,datetime.now().minute): importados = importados[importados.data < pd.to_datetime(date.today(),utc=True)]
                        if p.ajustar_numero: importados = ajustarNumero(importados)
                        if nome_modelo == 'Cotacao': 
                            importados.close.replace(to_replace=0,method='ffill',inplace=True)
                            importados.close.replace(to_replace=0,method='bfill',inplace=True)
                            importados = importados[importados.close > 0]
                        if len(p.campo_filtro_importados) > 0: importados = importados[getattr(importados,p.campo_filtro_importados) == p.filtro_importados]                    
                        if len(importados) > 0:
                            if indexRegistros != "": 
                                importados = importados.set_index(indexRegistros) if set(indexRegistros).issubset(importados.columns.values) else pd.DataFrame()
                            if p.existe_tabela: 
                                md = importados.index.get_level_values(importados.index.names.index('data')).min()
                                md =  pd.to_datetime(md,utc=True,infer_datetime_format=True)
                                registros = pd.DataFrame(modelo.objects.filter(Q(acao=self.id) & Q(data__gte=md)).values())
                                registros.reset_index(inplace=True)
                                if not registros.empty: registros = registros.set_index(indexRegistros)                      
                                # print(importados.index, registros.index,sep='\n')
                                importados = importados.loc[importados.index.difference(registros.index)]    
                                # print(importados.index)
                        
                        resultado = 'atualizado'
                        atualizarResultado = len(importados) > 0 and (p.intra_dia or p.periodo_atualizacao == 0)
                        if not importados.empty:
                            print('Atualizando', p.modelo, codigoAcao)                                     
                            if p.traduzir:   
                                tradutor = False                         
                                for it in importados.columns:
                                    if not it in importadosRename.values() and it != 'data': 
                                        ct = CampoTraduzido.objects.filter(Q(modelo=nome_modelo) & Q(original=it)).values()
                                        if ct.exists():
                                            importados.rename(columns={it : ct[0]['traduzido']}, inplace=True)
                                        else: 
                                            resultado, repetir = 'erro', False
                                            ci = CampoInexistente.objects.filter(Q(modelo=nome_modelo) & Q(original=it))
                                            if not ci.exists():
                                                if not tradutor: tradutor = Translator()
                                                CampoInexistente(modelo=nome_modelo, original=it, traduzido=subsituiMaiusculaPorUnderlineTraduz(tradutor,it), codigo=codigoAcao).save()
                                            else:
                                                ci.codigo += (',' + codigoAcao)
                                                ci.save()
                                if tradutor: del tradutor
                            if resultado == 'atualizado':
                                try:
                                    importados.reset_index(inplace=True)  
                                    importados.fillna(0,inplace=True)
                                    novas_instancias = [modelo(**criaInstanciaModelo(modelo,linha,importados.columns)) for idx_ii,linha in importados.iterrows()]
                                    modelo.objects.bulk_create(novas_instancias)
                                    if nome_modelo == 'DeclaracaoRenda': self.ajustarLPATrimestre4(importados.data.min())  
                                except Exception as inst:
                                    print(importados)
                                    estado = inst.args[0]
                                    print(f"Erro ao gravar as informações referentes a tabela {p.modelo} da ação {codigoAcao}", estado)
                                    dfErrosDic = pd.concat([dfErrosDic,pd.DataFrame({'tabela': [p.modelo], 'codigo': [codigoAcao], 'estado': [estado]})])
                                    resultado = estado
                    if repetir:
                        print('Repetindo', codigoAcao)
                if repetir: resultado = 'erro'
                if type(resultado) is str:
                    if 'No data available' in resultado: resultado = 'sem dados'
                else: resultado = 'erro'
                if len(resultadoGravado) > 0:
                    if resultado != resultadoGravado['resultado'][0]: # or len(resultadoGravado) > 1:
                        dt = pd.to_datetime(date.today(),utc=True,infer_datetime_format=True)
                        self.resultadoimportacao_set.filter(Q(modelo=p.modelo) & Q(data=dt)).delete()
                        atualizarResultado = True
                    else: atualizarResultado = False
                elif not (p.intra_dia or p.periodo_atualizacao == 0): atualizarResultado = True
                if atualizarResultado:
                    dt = pd.to_datetime(datetime.now(),utc=True,infer_datetime_format=True) 
                    resultadoGravado = ResultadoImportacao(acao_id=self.pk, modelo=p.modelo, data=dt, resultado=resultado, repeticoes=repeticoes)
                    try:
                        # print(resultadoGravado.data, resultadoGravado.acao_id, resultadoGravado.modelo)
                        resultadoGravado.save()
                    except Exception as inst:
                        print(resultadoGravado)
                        estado = inst.args[0]
                        print(f'Erro ao gravar as informações referentes aos resultados da importação da ação {codigoAcao}', estado)
            del ticker
        # return dfErrosDic

    def verificarFaltasDadosImportados(self):        
        modelos = ['Balanco','DeclaracaoRenda','FluxoCaixa']
        tipoPeriodo = {'3M': 4, '12M': 1}
        parametros = pd.DataFrame(ParametroImportacao.objects.filter(Q(biblioteca='yq') & Q(atualizar=True) & Q(modelo__in=modelos)).order_by('modelo').values())
        nome_modelo_anterior = ''
        for idxTab, p in parametros.iterrows():
            nome_modelo = p.modelo if len(p.sufixo) == 0 else p.modelo[:-len(p.sufixo)]
            if nome_modelo != nome_modelo_anterior:
                nome_modelo_anterior = nome_modelo
                modelo = apps.get_model('home', nome_modelo)
                indexRegistros = eval(p.index_registros)
                print(f'Verificando faltas no modelo {nome_modelo} da ação {self.codigo}')    
                registros = modelo.objects.filter(Q(acao=self.pk)).values_list(indexRegistros[0],'data__year',indexRegistros[2],indexRegistros[3])
                if len(registros) > 0:
                    anoi = registros.aggregate(Min('data__year'))
                    anoi['data__year__min'] = 2010 if anoi['data__year__min'] < 2010 else anoi['data__year__min']
                    anof = registros.aggregate(Max('data__year'))
                    for periodo in tipoPeriodo:
                        registrosEspec= pd.DataFrame(registros.filter(Q(tipo_periodo=periodo)).annotate(regs=Count('data__year')).filter(Q(data__year__gt=anoi['data__year__min']) & Q(data__year__lt=anof['data__year__max'])).order_by('data__year'))
                        for ano in range(anoi['data__year__min']+1,anof['data__year__max']):
                            regs = registrosEspec[registrosEspec[1]==ano].reset_index() if not registrosEspec.empty else pd.DataFrame()
                            if len(regs) > 0: 
                                if regs[4][0] != tipoPeriodo[periodo]:
                                    ResultadoAnaliseImportacao(acao_id=self.pk, modelo=nome_modelo, ano=ano, tipo_periodo=periodo, codigo_moeda=regs[3][0], quantidade=regs[4][0], tipo_problema='F').save()
                            else:
                                ResultadoAnaliseImportacao(acao_id=self.pk, modelo=nome_modelo, ano=ano, tipo_periodo=periodo, codigo_moeda='', quantidade=0, tipo_problema='F').save()

    def verificarDuplicidadeDadosImportados(self):   
        parametros = pd.DataFrame(ParametroImportacao.objects.filter(Q(biblioteca='yq') & Q(atualizar=True)).order_by('modelo').values())
        nome_modelo_anterior = ''
        for idxTab, p in parametros.iterrows():
            nome_modelo = p.modelo if len(p.sufixo) == 0 else p.modelo[:-len(p.sufixo)]
            if nome_modelo != nome_modelo_anterior:
                nome_modelo_anterior = nome_modelo
                modelo = apps.get_model('home', nome_modelo)
                indexRegistros = eval(p.index_registros)
                print(f'Verificando duplicidade no modelo {nome_modelo} da ação {self.codigo}')    
                registros = pd.DataFrame(modelo.objects.filter(Q(acao=self.pk)).values_list(*indexRegistros).annotate(Count('data')).filter(data__count__gt=1))
                if len(registros) > 0: 
                    ResultadoAnaliseImportacao(acao_id=self.pk, modelo=nome_modelo, ano=0, tipo_periodo='', codigo_moeda='', quantidade='', tipo_problema='D').save()
                    print(f'Erro no modelo {nome_modelo} da ação {self.codigo}', registros, sep='\n')                    

    def ajustarDadosImportados(self):  
        if self.cotacao_set.filter(fechamento=0): 
            cotacoes = self.cotacao_set.all().order_by('data')
            cotacaoInicial = self.cotacao_set.filter(fechamento__gt=0).order_by('data')[:1]
            if cotacaoInicial:
                fechamento_anterior = cotacaoInicial[0].fechamento
                for cotacao in cotacoes:
                    if cotacao.fechamento == 0:
                        cotacao.fechamento = fechamento_anterior
                        cotacao.save()
                    fechamento_anterior = cotacao.fechamento
        self.cotacao_set.filter(fechamento=0).delete()

    def ajustarLPATrimestre4(self, dataInicial=None):  
        # Ajustar valor LPA quarto trimestre para que a soma dos trimestres seja igual ao anual
        campos = ['lpa_basicos', 'lpa_diluidos']
        for c in campos:
            dfAno = pd.DataFrame(self.declaracaorenda_set.filter(Q(tipo_periodo='12M')&~Q(**{c:0})).values('data',c) if not dataInicial else self.declaracaorenda_set.filter(Q(tipo_periodo='12M')&~Q(**{c:0})&Q(data__gte=dataInicial)).values('data',c))
            for idx, it in dfAno.iterrows():
                dadosLPA = self.declaracaorenda_set.filter(Q(tipo_periodo='3M')&Q(data__year=it.data.year)).aggregate(soma_lpa=Sum(c),periodos=Count('acao_id'))
                if dadosLPA['soma_lpa']:
                    if it[c] != round(dadosLPA['soma_lpa'],3) and dadosLPA['periodos'] == 4:
                        qsTri = self.declaracaorenda_set.filter(Q(tipo_periodo='3M')&Q(data=it.data)&Q(**{c:0})).first() 
                        if qsTri: 
                            setattr(qsTri, c, round(it[c] - dadosLPA['soma_lpa'],3))
                            qsTri.save()

    def apresentaInfo(self,engine):
        tabelas = pd.read_sql("select * from tabela_yq;" ,con=engine)        
        for idxTab, p in tabelas.iterrows():
            tabela = p.tabela
            if len(p.sufixo) > 0: tabela = tabela[:-len(p.sufixo)]
            codigos = [self.codigo + '3.SA', self.codigo + '4.SA', self.codigo + '5.SA', self.codigo + '6.SA', self.codigo + '11.SA']        
            for codigo_acao in codigos:
                try:
                    registros = pd.read_sql("select * from " + tabela + " where codigo = '" + codigo_acao + "' limit 1;" ,con=engine)
                    if len(registros) > 0:
                        print(tabela)
                        print(registros.transpose())
                except:
                    print('Tabela ' + tabela + ' inexistente.')
    
    def analisarHistoricoIndicadorFundamentalista(self, engine):
        indicadores = pd.read_sql("select * from campo_traduzido where not prioridade is null order by prioridade;" ,con=engine)        
        resultado = pd.Series()
        for idx, indicador in indicadores.iterrows():
            valores = pd.read_sql("select " + indicador.traduzido + " from " + indicador.tabela + " where codigo = '" + self.codigo +  "' " + indicador.filtro + " order by " + indicador.ordem + " desc;" ,con=engine)        
            resultado[idx] = valores.loc[0][0] / (valores.mean() + valores.std()) #  = 1 média
        return resultado
    
    def prepararDadosFundamentos(self, PAnalise):
        df = pd.DataFrame()
        colunasExcluidas = ['id','acao_id','codigo_moeda','tipo_periodo']
        dfBalanco = pd.DataFrame(self.balanco_set.filter(Q(tipo_periodo=PAnalise.tipo_periodo[0])&Q(codigo_moeda=PAnalise.codigo_moeda[0])&Q(data__gte=PAnalise.data__min[0])).values())
        if not dfBalanco.empty:
            dfBalanco.drop(columns=colunasExcluidas,inplace=True)
            dfBalanco.data = dfBalanco.data + timedelta(days=diasAcrescimoDadosFundamentos)
            dfDeclaracaoRenda = pd.DataFrame(self.declaracaorenda_set.filter(Q(tipo_periodo=PAnalise.tipo_periodo[0])&Q(codigo_moeda=PAnalise.codigo_moeda[0])&Q(data__gte=PAnalise.data__min[0])).values())
            if not dfDeclaracaoRenda.empty:
                colunasDuplicadas = [c for c in dfDeclaracaoRenda.columns if c in dfBalanco.columns and not c == 'data']
                dfDeclaracaoRenda.drop(columns=colunasExcluidas+colunasDuplicadas,inplace=True)
                dfDeclaracaoRenda.data = dfDeclaracaoRenda.data + timedelta(days=diasAcrescimoDadosFundamentos)
                df = dfBalanco.merge(dfDeclaracaoRenda, how='outer', left_on='data', right_on='data')
            dfFluxoCaixa = pd.DataFrame(self.fluxocaixa_set.filter(Q(tipo_periodo=PAnalise.tipo_periodo[0])&Q(codigo_moeda=PAnalise.codigo_moeda[0])&Q(data__gte=PAnalise.data__min[0])).values())
            if not dfFluxoCaixa.empty:
                colunasDuplicadas = [c for c in dfFluxoCaixa.columns if c in df.columns and not c == 'data']
                dfFluxoCaixa.drop(columns=colunasExcluidas+colunasDuplicadas,inplace=True)
                dfFluxoCaixa.data = dfFluxoCaixa.data + timedelta(days=diasAcrescimoDadosFundamentos)
                df = df.merge(dfFluxoCaixa, how='outer', left_on='data', right_on='data')
            df = df.sort_values(by=['data']).reset_index(drop=True)
            df = df.replace(to_replace=0, method='ffill') if PAnalise.completo[0] else df.replace(to_replace=0, method='ffill', limit=91)

        # print(df.info(verbose=True))
        return df
    
    def preverPreco(self, df, PAnalise):
        df.sort_values(by=['data'],inplace=True)
        df.reset_index(inplace=True, drop=True)
                
        dfX = pd.DataFrame()
        dfX['day'], dfX['dayofyear'],dfX['month'], dfX['weekday'] = df.data.dt.day, df.data.dt.day_of_year, df.data.dt.month, df.data.dt.weekday
        cyclical = CyclicalTransformer(variables=None, drop_original=True)
        dfX = cyclical.fit_transform(dfX)
        df['day_sin'], df['dayofyear_sin'],df['month_sin'], df['weekday_sin'], df['day_cos'], df['dayofyear_cos'],df['month_cos'], df['weekday_cos'] = dfX['day_sin'], dfX['dayofyear_sin'],dfX['month_sin'], dfX['weekday_sin'], dfX['day_cos'], dfX['dayofyear_cos'],dfX['month_cos'], dfX['weekday_cos']
        df['ano'] = df.data.dt.year

        dfX = df[-(diasAnalise + diasPrevisao):-diasPrevisao:]
        dfY = pd.DataFrame()
        dfY['real'] = dfX['fechamento']
        dfXPrevisao = df[-diasPrevisao::]
        dfYPrevisao = pd.DataFrame()
        dfYPrevisao['real'] = dfXPrevisao['fechamento']
        dfYPrevisao['previsao'] = 0
        dfX = dfX.drop(['data','fechamento','abertura','maximo','minimo'], axis=1)
        dfXPrevisao = dfXPrevisao.drop(['data','fechamento','abertura','maximo','minimo'], axis=1)

        # print(dfXPrevisao.max().max())
        # print(dfXPrevisao.idxmax()['ativos_totais'])
        # print(dfXPrevisao.idxmax(axis=1))
        # print(dfXPrevisao.loc[dfXPrevisao.idxmax()[0],dfXPrevisao.idxmax(axis=1)])
        
        try:
            dfXTrain, dfXTest, dfYTrain, dfYTest = sklearn.model_selection.train_test_split(
                dfX, dfY, test_size=0.3, random_state=1)
            # automl = load('/home/pogere/bot/anls-prc.joblib')
            automl = autosklearn.regression.AutoSklearnRegressor(
                time_left_for_this_task=360
                )
            automl.fit(dfXTrain, dfYTrain, dataset_name='Análise Preço')
            dump(automl, '/home/pogere/bot/anls-prc.joblib')
            # dump(automl, '/home/pogere/bot/anls-prc' + self.codigo[:5:] + '.joblib')
            
            ensemble_dict = automl.show_models()
            print(ensemble_dict)
            print(automl.leaderboard(detailed=True))

            print(automl.score(dfXTest,dfYTest))
            print(automl.sprint_statistics())
            models = automl.get_models_with_weights()

            dfYPrevisao['previsao'] = automl.predict(dfXPrevisao)
            print(automl.score(dfXPrevisao,dfYPrevisao['real']))
            dfYPrevisao.reset_index(inplace=True, drop=True)

            dfXPrevisao = df[-diasPrevisao::].copy()        
            dfXPrevisao.reset_index(inplace=True, drop=True)
            dfYPrevisao['data'] = dfXPrevisao['data']
            dfYPrevisao.set_index(['data'], inplace=True)
            # print(dfYPrevisao)
            # dfYPrevisao.plot()
            # plt.show()

            dfYPrevisao.reset_index(inplace=True)
            dfXPrevisao['previsao'] = dfYPrevisao['previsao']
            dfXPrevisao = dfXPrevisao.drop(['day_sin','dayofyear_sin','month_sin','weekday_sin','day_cos','dayofyear_cos','month_cos','weekday_cos'], axis=1)
            print(dfYPrevisao)
        except Exception as inst:                            
            if len(inst.args)>0: 
                print(inst.args[0])
        p = 0
        dfYPrevisao = dfYPrevisao[dfYPrevisao.previsao > 0]
        return dfYPrevisao

    def aplicarEventosNoPreco(self, engine):
        p = 0
        return p

    def identificarEspiral(self, engine):
        df = pd.DataFrame
        return df
    
    def elaborarAnalise(self, engine):
        df = pd.DataFrame
        return df
    
    def definirParametrosDadosAnalise(self):
        df = pd.DataFrame(self.balanco_set.values('tipo_periodo','codigo_moeda').annotate(Min('data'),Max('data')))
        dfRetorno = pd.DataFrame()
        if not df.empty:
            for moeda in df.codigo_moeda.drop_duplicates().to_list():
                tipo_periodo, completo = '', False
                qtdeBalTri = self.balanco_set.filter(Q(tipo_periodo='3M')&Q(codigo_moeda=moeda)).values('tipo_periodo').aggregate(Count('tipo_periodo'))['tipo_periodo__count']
                qtdeBalTriAno = pd.DataFrame(self.balanco_set.filter(Q(tipo_periodo='3M')&Q(codigo_moeda=moeda)).values('data__year').annotate(Count('data__year')).order_by('data__year')).rename(columns={'data__year':'ano','data__year__count':'cont'})[1:-1].reset_index()
                qtdeBalAno = pd.DataFrame(self.balanco_set.filter(Q(tipo_periodo='12M')&Q(codigo_moeda=moeda)).values('data__year').annotate(Count('data__year')).order_by('data__year')).rename(columns={'data__year':'ano','data__year__count':'cont'})
                if not(qtdeBalAno.empty and qtdeBalTriAno.empty):
                    if qtdeBalAno.empty:
                        if not qtdeBalTriAno.empty:
                            # tipo_periodo =  '3M' if (qtdeBalTriAno.loc[len(qtdeBalTriAno)-1,'ano'] == datetime.now().year - 1) and (((datetime.now().year) - len(qtdeBalTriAno)) == qtdeBalTriAno.loc[0,'ano']) else ''
                            tipo_periodo =  '3M' if qtdeBalTri >= quantidadeMinimaTrimestres else ''
                    elif qtdeBalTriAno.empty:
                        if not qtdeBalAno.empty:
                            # tipo_periodo = '12M' if (qtdeBalAno.loc[len(qtdeBalAno)-1,'ano'] == datetime.now().year - 1) and (((datetime.now().year) - len(qtdeBalAno)) == qtdeBalAno.loc[0,'ano']) else ''
                            tipo_periodo = '12M' if len(qtdeBalAno) >= quantidadeMinimaAnos else ''
                    else:
                        # tipo_periodo = '3M' if (qtdeBalTriAno.loc[len(qtdeBalTriAno)-1,'ano'] == datetime.now().year - 1) and (((datetime.now().year) - len(qtdeBalTriAno)) == qtdeBalTriAno.loc[0,'ano']) else ''
                        tipo_periodo =  '3M' if qtdeBalTri >= quantidadeMinimaTrimestres else ''
                        if not tipo_periodo:  
                            # tipo_periodo = '12M' if (qtdeBalAno.loc[len(qtdeBalAno)-1,'ano'] == datetime.now().year - 1) and (((datetime.now().year) - len(qtdeBalAno)) == qtdeBalAno.loc[0,'ano']) else ''
                            tipo_periodo = '12M' if len(qtdeBalAno) >= quantidadeMinimaAnos else ''
                            
                    if tipo_periodo:
                        if tipo_periodo == '3M':
                            completo = (len(qtdeBalTriAno) == len(qtdeBalTriAno[qtdeBalTriAno.cont == 4])) and (qtdeBalTriAno.loc[len(qtdeBalTriAno)-1,'ano'] == datetime.now().year - 1) and (((datetime.now().year) - len(qtdeBalTriAno)) == qtdeBalTriAno.loc[0,'ano'])
                        else:
                            completo = (len(qtdeBalAno) == len(qtdeBalAno[qtdeBalAno.cont == 1])) and (qtdeBalAno.loc[len(qtdeBalAno)-1,'ano'] == datetime.now().year - 1) and (((datetime.now().year) - len(qtdeBalAno)) == qtdeBalAno.loc[0,'ano'])
                        dfAux = df[(df.tipo_periodo == tipo_periodo) & (df.codigo_moeda == moeda)].reset_index(drop=True).copy()
                        if not dfAux.empty:
                            dfAux['periodos'] = qtdeBalTri if tipo_periodo == '3M' else len(qtdeBalAno)
                            dfAux['completo'] = completo
                            dfRetorno = pd.concat([dfRetorno,dfAux])
            if len(dfRetorno) > 1:
                max_periodos = dfRetorno.periodos.max()
                dfAux = dfRetorno[((dfRetorno.periodos == max_periodos) | (dfRetorno.periodos >= quantidadeMinimaTrimestres)) & (dfRetorno.tipo_periodo == '3M')]
                if dfAux.empty:
                    dfAux = dfRetorno[((dfRetorno.periodos == max_periodos) | (dfRetorno.periodos >= quantidadeMinimaAnos)) & (dfRetorno.tipo_periodo == '12M')]
                if len(dfAux) > 1:
                        dfRetorno = dfAux[dfRetorno.periodos == dfAux.periodos.max()][:1]
        return dfRetorno
    
    def prepararDadosAnalise(self, dfIndice, PAnalise):
        df = pd.DataFrame()
        dataInicioCotacao = self.cotacao_set.aggregate(Min('data'))['data__min']
        if dataInicioCotacao:
            if dataInicioCotacao > PAnalise.data__min[0]: PAnalise.loc[0,'data__min'] = dataInicioCotacao
            dataInicioCotacao = PAnalise.data__min[0] + timedelta(days=diasAcrescimoDadosFundamentos)
            df = pd.DataFrame(self.cotacao_set.filter(Q(data__gte=dataInicioCotacao)).values())
            if not dfIndice.empty: dfIndice = dfIndice[dfIndice.data >= dataInicioCotacao]
            if not df.empty:
                df.drop(columns=['id','preco_ajustado','acao_id'], inplace=True)
                if not dfIndice.empty: df = df.merge(dfIndice, how='outer', left_on='data', right_on='data').sort_values('data').reset_index(drop=True)
                df.fillna(method="ffill", inplace=True)
                df = df[df.fechamento > 0]
                dfFundamentos = self.prepararDadosFundamentos(PAnalise)
                if not dfFundamentos.empty:
                    df = df.merge(dfFundamentos, how='outer', left_on='data', right_on='data').sort_values('data').reset_index(drop=True)
                    df.fillna(method="ffill", limit=91, inplace=True)
                    df = df[(df.acoes_ordinarias > 0) & (df.patrimonio_liquido > 0)]
                df.fillna(0,inplace=True)
        return df

    def analiseTecnica(self, cotacaoAcao):
        tipoMedia, varMinima, periodoIndicadores = 'media_exponencial', 0.1, '365D'
        diasRetornoMediaAlta, diasRetornoMediaAltaExponencial, valorMedioCorrente, valorCorrente, precoCompra, precoCompraExponencial, precoVenda, precoVendaMaximo, precoVendaMaximoExponencial = 0, 0, 0, 0, 0, 0, 0, 0, 0
        diasRetornoMediaQueda, diasRetornoMediaQuedaExponencial = 0, 0

        resultadoAnalise = pd.DataFrame
        if not cotacaoAcao.empty:
            cotacaoAcao = cotacaoAcao[['data', 'fechamento', 'volume']].copy()
            cotacaoAcao.set_index(['data'],inplace=True,append=False,drop=True)
            cotacaoAcao['periodo'] = pd.DatetimeIndex(cotacaoAcao.index)
            cotacaoAcao.sort_index(inplace=True)
            
            cotacaoAcao['minimo'] = cotacaoAcao.fechamento.rolling(periodoIndicadores).min() 
            cotacaoAcao['maximo'] = cotacaoAcao.fechamento.rolling(periodoIndicadores).max() 
            cotacaoAcao['media'] = cotacaoAcao.fechamento.rolling(periodoIndicadores).mean() 
            cotacaoAcao['desvio'] = cotacaoAcao.fechamento.rolling(periodoIndicadores).std() 
            cotacaoAcao['media_exponencial'] = cotacaoAcao.fechamento.ewm(halflife='90 days', times=cotacaoAcao.periodo).mean() 
            cotacaoAcao['variacao'] = (cotacaoAcao['fechamento'] - cotacaoAcao[tipoMedia]) / cotacaoAcao[tipoMedia]    

            # Criar os df's varAbaixo e varAcima contendo os extremos de variação em cada trimestre
            grupoAnalise = cotacaoAcao.groupby(pd.Grouper(key = 'periodo', freq='Q'))
            
            dfGrupo = grupoAnalise.variacao.min()
            dfGrupo.dropna(inplace=True)
            varAbaixo = pd.DataFrame()
            for idx2,item2 in dfGrupo.items():
                df = grupoAnalise.get_group(idx2)
                df = df[df.variacao == item2].tail(1)
                varAbaixo = df if len(varAbaixo) == 0 else pd.concat([varAbaixo,df])
            if not varAbaixo.empty:
                varAbaixo = varAbaixo[varAbaixo.variacao < -varMinima]
                varAbaixo['data_retorno_media'] = None 
                varAbaixo['dias_retorno_media'] = None 
                for idx2, item2 in varAbaixo.iterrows():
                    corteData = cotacaoAcao[(cotacaoAcao.index >= idx2) & (cotacaoAcao.fechamento >= item2[tipoMedia])]
                    varAbaixo.loc[idx2,'data_retorno_media'] = None if len(corteData) == 0 else pd.to_datetime(corteData.index.values[0])
                    varAbaixo.loc[idx2,'dias_retorno_media'] = None if len(corteData) == 0 else (pd.to_datetime(corteData.index.values[0],utc=True) - idx2).days
                
            dfGrupo = grupoAnalise.variacao.max()
            dfGrupo.dropna(inplace=True)
            varAcima = pd.DataFrame()
            for idx2,item2 in dfGrupo.items():
                df = grupoAnalise.get_group(idx2)
                df = df[df.variacao == item2].head(1)
                varAcima = df if len(varAcima) == 0 else pd.concat([varAcima,df])
            if not varAcima.empty:
                varAcima = varAcima[varAcima.variacao > varMinima]
                varAcima['data_retorno_media'] = None
                varAcima['dias_retorno_media'] = None 
                for idx2, item2 in varAcima.iterrows():
                    corteData = cotacaoAcao[(cotacaoAcao.index >= idx2) & (cotacaoAcao.fechamento <= item2[tipoMedia])]
                    varAcima.loc[idx2,'data_retorno_media'] = None if len(corteData) == 0 else pd.to_datetime(corteData.index.values[0])
                    varAcima.loc[idx2,'dias_retorno_media'] = None if len(corteData) == 0 else (pd.to_datetime(corteData.index.values[0],utc=True) - idx2).days
                
            # Criar os indicadores da ação
            if not varAbaixo.empty and not varAcima.empty:
                mediaQueda = varAbaixo.variacao.mean()
                mediaQuedaExponencial = varAbaixo.variacao.ewm(halflife='90 days', times=varAbaixo.periodo).mean().tail(1).values[0] if len(varAbaixo) > 0 else 0
                df = remove_outlier(varAbaixo,'dias_retorno_media')
                diasRetornoMediaQueda = df.dias_retorno_media.mean()
                diasRetornoMediaQuedaExponencial = df.dias_retorno_media.ewm(halflife='90 days', times=df.periodo).mean().tail(1).values[0] if len(df) > 0 else 0
                mediaSubida = varAcima.variacao.mean()
                mediaSubidaExponencial = varAcima.variacao.ewm(halflife='90 days', times=varAcima.periodo).mean().tail(1).values[0] if len(varAcima) > 0 else 0
                df = remove_outlier(varAcima,'dias_retorno_media')
                diasRetornoMediaAlta = df.dias_retorno_media.mean()
                diasRetornoMediaAltaExponencial = df.dias_retorno_media.ewm(halflife='90 days', times=df.periodo).mean().tail(1).values[0] if len(df) > 0 else 0
                valorMedioCorrente = cotacaoAcao.tail(1)[tipoMedia][0]
                valorCorrente = cotacaoAcao.tail(1).fechamento[0]
                precoCompra = valorMedioCorrente * (1 + mediaQueda)
                precoCompraExponencial = valorMedioCorrente * (1 + mediaQuedaExponencial)
                precoVenda = valorMedioCorrente
                precoVendaMaximo = valorMedioCorrente * (1 + mediaSubida)
                precoVendaMaximoExponencial = valorMedioCorrente * (1 + mediaSubidaExponencial)

        resultadoAnalise = pd.DataFrame({'valor_corrente': [valorCorrente], 
                                        'valor_medio_corrente': [valorMedioCorrente], 
                                        'preco_compra': [precoCompra], 
                                        'preco_compra_exponencial': [precoCompraExponencial], 
                                        'preco_venda': [precoVenda], 
                                        'preco_venda_maximo':[precoVendaMaximo], 
                                        'preco_venda_maximo_exponencial':[precoVendaMaximoExponencial], 
                                        'dias_retorno_medio_queda': [diasRetornoMediaQueda], 
                                        'dias_retorno_medio_queda_exponencial': [diasRetornoMediaQuedaExponencial], 
                                        'dias_retorno_medio_alta': [diasRetornoMediaAlta],
                                        'dias_retorno_medio_alta_exponencial': [diasRetornoMediaAltaExponencial]
                                        })
        return resultadoAnalise
        
    def projetar(self, dfIndice, projecao):
        projecaoAcao = self.projecaoacao_set.filter(projecao=projecao)
        inicio = datetime.now()
        print(inicio)
        PAnalise = self.definirParametrosDadosAnalise()
        if not PAnalise.empty:        
            df = self.prepararDadosAnalise(dfIndice,PAnalise)
            if not df.empty: 
                dfProjecao = self.analiseTecnica(df)
                if not projecaoAcao:
                    dfPreco = self.preverPreco(df,PAnalise)                    
                    if dfPreco.empty: indicacao, precoIA, dataPrecoIA = 'Venda', 0, pd.to_datetime(date(2022,1,1),utc=True,infer_datetime_format=True)
                    else: 
                        indicacao = 'Compra' if dfPreco.loc[len(dfPreco)-1,'real'] < dfPreco.loc[len(dfPreco)-1,'previsao'] else 'Venda'
                        precoIA, dataPrecoIA = dfPreco.loc[len(dfPreco)-1,'previsao'], dfPreco.loc[len(dfPreco)-1,'data']
                    projecaoAcao = ProjecaoAcao(projecao=projecao, acao=self, tipo = indicacao, preco_ia = precoIA, data_preco_ia = dataPrecoIA).save()
                else: projecaoAcao = projecaoAcao[0]
                projecaoAcao.preco_corrente=dfProjecao.valor_corrente[0]
                projecaoAcao.preco_medio=dfProjecao.valor_medio_corrente[0]
                projecaoAcao.preco_compra=dfProjecao.preco_compra[0]
                projecaoAcao.preco_venda=dfProjecao.preco_venda[0]
                projecaoAcao.preco_venda_maximo=dfProjecao.preco_venda_maximo_exponencial[0]
                projecaoAcao.rentabilidade=((dfProjecao.preco_venda[0]/dfProjecao.preco_compra[0])-1)*100 if dfProjecao.preco_compra[0] > 0 else 0
                projecaoAcao.rentabilidade_maxima=((dfProjecao.preco_venda_maximo_exponencial[0]/dfProjecao.preco_compra[0])-1)*100 if dfProjecao.preco_compra[0] > 0 else 0
                projecaoAcao.dias_operacao_compra=dfProjecao.dias_retorno_medio_alta_exponencial[0]
                projecaoAcao.dias_operacao_venda=dfProjecao.dias_retorno_medio_queda_exponencial[0]
                projecaoAcao.tempo_projecao=(datetime.now() - inicio).total_seconds()/60
                projecaoAcao.save()
                # dfProjecao = self.calcularIndicadoresRankings(dfProjecao)
                # dfProjecao = self.aplicarEventosNoPreco(dfProjecao)
                # dfProjecao = self.identificarEspiral(dfProjecao)        
                # dfProjecao = self.concluirProjecao(dfProjecao)

class Projecao(models.Model):
    data = models.DateTimeField('data',default='2022-01-01 00:00:00-03',db_index=True, unique=True)

    class Meta:
            ordering = ['-data']

    def projetar(self):
        dataInicial = pd.to_datetime(datetime.today() - timedelta(days=diasMediaVolumeMinimo),utc=True,infer_datetime_format=True)
        # dfIndice = prepararIndicesAnalise()
        # for acao in Acao.objects.filter(empresa__ativo=True):
        # for acao in Acao.objects.filter(Q(empresa__ativo=True)&Q(cotacao__data__gte=dataInicial)).annotate(media_volume=Avg('cotacao__volume')).filter(media_volume__gte=mediaVolumeMinimo).order_by('codigo'):
        # # for acao in Acao.objects.filter(codigo__gte='AGRO3.SA'):
            # print(acao.codigo)
        #     acao.projetar(dfIndice, self)

        # projecoes = ProjecaoAcao.objects.filter(acao__cotacao__data__gte=dataInicial).annotate(media_volume=Avg('acao__cotacao__volume')).filter(media_volume__lt=mediaVolumeMinimo).order_by('acao__codigo')
        self.projecaoacao_set.filter(acao__empresa__ativo=False).delete()

        for ranking in Ranking.objects.filter(~Q(propriedade='')).order_by('-modelo','propriedade'): 
            ranking.rankear(self)
        
        # for ranking in Ranking.objects.filter(id__in=(16,)): 
        #     ranking.rankear(self)
    
class CVMTabela(models.Model):
    nome = models.CharField(max_length=200,db_index=True,unique=True)
    modelo = models.CharField(max_length=100,db_index=True,default='')
    niveis = models.IntegerField(default=3)
    importar = models.BooleanField(default=True)
    acumulado = models.BooleanField(default=False)

    class Meta:
        db_table = 'home_cvm_tabela'
        ordering = ['modelo']

class CVMCampo(models.Model):
    tabela = models.ForeignKey(CVMTabela, on_delete=models.CASCADE,db_index=True)
    codigo = models.CharField(max_length=200,db_index=True)
    nome = models.CharField(max_length=200,db_index=True)
    campo = models.CharField(max_length=200,db_index=True,default='')

    class Meta:
        db_table = 'home_cvm_campo'
        unique_together = [['tabela', 'codigo']]
        ordering = ['codigo']

class CVMCampoNome(models.Model):
    campo = models.ForeignKey(CVMCampo, on_delete=models.CASCADE,db_index=True)
    empresas = models.ManyToManyField(Empresa, db_index=True)
    nome = models.CharField(max_length=200,db_index=True)

    class Meta:
        db_table = 'home_cvm_campo_nome'
        unique_together = [['campo','nome']]
        ordering = ['campo','nome']

class CVMArquivo(models.Model):
    nome = models.CharField(max_length=200,db_index=True)
    data_criado = models.DateTimeField('data',default='2022-01-01 00:00:00-03')
    data_modificado = models.DateTimeField('data',default='2022-01-01 00:00:00-03')
    sucesso = models.BooleanField(default=False)

    class Meta:
        db_table = 'home_cvm_arquivo'
        unique_together = [['nome','data_modificado']]
        ordering = ['nome','data_modificado']

class CVMModelo(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE,db_index=True)
    data_inicio_exercicio = models.DateTimeField('data',default='1900-01-01 00:00:00-03',db_index=True)
    data_fim_exercicio = models.DateTimeField('data',default='1900-01-01 00:00:00-03',db_index=True)
    data_referencia = models.DateTimeField('data',default='1900-01-01 00:00:00-03',db_index=True)
    ordem_exercicio = models.CharField(max_length=30,default='')
    versao = models.IntegerField(default=0,db_index=True)
    moeda = models.CharField(max_length=100,db_index=True,default='')
    escala_moeda = models.CharField(max_length=100,default='')
    tipo_periodo = models.CharField(max_length=3,db_index=True,default='3M')

    class Meta:
        abstract = True
        ordering = ['empresa','data_fim_exercicio']        

class CVMComposicaoCapital(CVMModelo):
    on_mercado    = models.FloatField(default=0)
    on_tesouraria    = models.FloatField(default=0)
    pn_mercado    = models.FloatField(default=0)
    pn_tesouraria    = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_composicao_capital'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMBalancoAtivo(CVMModelo):
    amortizacao_acumulada    = models.FloatField(default=0)
    aplicacoes_financeiras   = models.FloatField(default=0)
    ativo_circulante         = models.FloatField(default=0)
    ativo_nao_circulante     = models.FloatField(default=0)
    ativo_realizavel_longo_prazo     = models.FloatField(default=0)
    ativo_total      = models.FloatField(default=0)
    ativos_biologicos        = models.FloatField(default=0)
    ativos_fiscais   = models.FloatField(default=0)
    ativos_nao_correntes_venda       = models.FloatField(default=0)
    ativos_operacoes_descontinuadas  = models.FloatField(default=0)
    caixa_equivalentes_caixa         = models.FloatField(default=0)
    contas_receber   = models.FloatField(default=0)
    depositos_compulsorios_banco_central     = models.FloatField(default=0)
    depositos_compulsorios_banco_central_brasil      = models.FloatField(default=0)
    depreciacao_acumulada    = models.FloatField(default=0)
    despesas_antecipadas     = models.FloatField(default=0)
    direito_uso_arrendamento         = models.FloatField(default=0)
    estoques         = models.FloatField(default=0)
    goodwill         = models.FloatField(default=0)
    imobilizado      = models.FloatField(default=0)
    imobilizado_uso  = models.FloatField(default=0)
    imobilizado1     = models.FloatField(default=0)
    imposto_renda_contribuicao_social_correntes      = models.FloatField(default=0)
    imposto_renda_contribuicao_social_diferidos      = models.FloatField(default=0)
    intangiveis      = models.FloatField(default=0)
    intangivel       = models.FloatField(default=0)
    intangivel1      = models.FloatField(default=0)
    investimentos    = models.FloatField(default=0)
    investimentos1   = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_ativos    = models.FloatField(default=0)
    outros_ativos_circulantes        = models.FloatField(default=0)
    outros_ativos_circulantes1       = models.FloatField(default=0)
    outros_investimentos     = models.FloatField(default=0)
    outros1  = models.FloatField(default=0)
    participacoes_coligadas  = models.FloatField(default=0)
    participacoes_controladas_conjunto       = models.FloatField(default=0)
    propriedades_investimento        = models.FloatField(default=0)
    tributos_diferidos       = models.FloatField(default=0)
    tributos_recuperar       = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_balanco_ativo'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMBalancoAtivoIndividual(CVMModelo):
    amortizacao_acumulada    = models.FloatField(default=0)
    aplicacoes_financeiras   = models.FloatField(default=0)
    ativo_circulante         = models.FloatField(default=0)
    ativo_nao_circulante     = models.FloatField(default=0)
    ativo_realizavel_longo_prazo     = models.FloatField(default=0)
    ativo_total      = models.FloatField(default=0)
    ativos_biologicos        = models.FloatField(default=0)
    ativos_nao_correntes_venda       = models.FloatField(default=0)
    ativos_operacoes_descontinuadas  = models.FloatField(default=0)
    caixa_equivalentes_caixa         = models.FloatField(default=0)
    contas_receber   = models.FloatField(default=0)
    depreciacao_acumulada    = models.FloatField(default=0)
    despesas_antecipadas     = models.FloatField(default=0)
    diferido         = models.FloatField(default=0)
    direito_uso_arrendamento         = models.FloatField(default=0)
    estoques         = models.FloatField(default=0)
    goodwill         = models.FloatField(default=0)
    imobilizado      = models.FloatField(default=0)
    imobilizado_uso  = models.FloatField(default=0)
    imobilizado1     = models.FloatField(default=0)
    imposto_renda_contribuicao_social_correntes      = models.FloatField(default=0)
    imposto_renda_contribuicao_social_diferidos      = models.FloatField(default=0)
    intangiveis      = models.FloatField(default=0)
    intangivel       = models.FloatField(default=0)
    intangivel1      = models.FloatField(default=0)
    intangivel2      = models.FloatField(default=0)
    investimentos    = models.FloatField(default=0)
    investimentos1   = models.FloatField(default=0)
    operacoes_arrendamento_mercantil         = models.FloatField(default=0)
    operacoes_credito        = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_ativos    = models.FloatField(default=0)
    outros_ativos_circulantes        = models.FloatField(default=0)
    outros_creditos  = models.FloatField(default=0)
    outros_investimentos     = models.FloatField(default=0)
    outros_valores_bens      = models.FloatField(default=0)
    outros_valores_bens1     = models.FloatField(default=0)
    outros1  = models.FloatField(default=0)
    participacoes_coligadas  = models.FloatField(default=0)
    participacoes_controladas        = models.FloatField(default=0)
    participacoes_controladas_conjunto       = models.FloatField(default=0)
    propriedades_investimento        = models.FloatField(default=0)
    tributos         = models.FloatField(default=0)
    tributos_recuperar       = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_balanco_ativo_individual'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMBalancoPassivo(CVMModelo):
    ajustes_acumulados_conversao     = models.FloatField(default=0)
    ajustes_acumulados_conversao1    = models.FloatField(default=0)
    ajustes_avaliacao_patrimonial    = models.FloatField(default=0)
    ajustes_avaliacao_patrimonial1   = models.FloatField(default=0)
    capital_social_realizado         = models.FloatField(default=0)
    capital_social_realizado1        = models.FloatField(default=0)
    correntes        = models.FloatField(default=0)
    credores_diversos_pais   = models.FloatField(default=0)
    diferidos        = models.FloatField(default=0)
    emprestimos_financiamentos       = models.FloatField(default=0)
    emprestimos_financiamentos1      = models.FloatField(default=0)
    emprestimos_repasses     = models.FloatField(default=0)
    fornecedores     = models.FloatField(default=0)
    imposto_renda_contribuicao_social_correntes      = models.FloatField(default=0)
    imposto_renda_contribuicao_social_diferidas      = models.FloatField(default=0)
    lucros_prejuizos_acumulados      = models.FloatField(default=0)
    lucros_prejuizos_acumulados1     = models.FloatField(default=0)
    lucros_receitas_apropriar        = models.FloatField(default=0)
    negociacao_intermediacao_valores         = models.FloatField(default=0)
    obrigacoes_aquisicao_bens_direitos       = models.FloatField(default=0)
    obrigacoes_convenios_oficiais    = models.FloatField(default=0)
    obrigacoes_fiscais       = models.FloatField(default=0)
    obrigacoes_sociais_trabalhistas  = models.FloatField(default=0)
    outras   = models.FloatField(default=0)
    outras_obrigacoes        = models.FloatField(default=0)
    outras_obrigacoes1       = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_passivos  = models.FloatField(default=0)
    outros_passivos1         = models.FloatField(default=0)
    outros_passivos2         = models.FloatField(default=0)
    outros_resultados_abrangentes    = models.FloatField(default=0)
    outros_resultados_abrangentes1   = models.FloatField(default=0)
    participacao_acionistas_nao_controladores        = models.FloatField(default=0)
    participacao_acionistas_nao_controladores1       = models.FloatField(default=0)
    passivo_circulante       = models.FloatField(default=0)
    passivo_nao_circulante   = models.FloatField(default=0)
    passivo_planos_capitalizacao     = models.FloatField(default=0)
    passivo_total    = models.FloatField(default=0)
    passivos_fiscais         = models.FloatField(default=0)
    passivos_fiscais1        = models.FloatField(default=0)
    passivos_sobre_ativos_nao_correntes_venda        = models.FloatField(default=0)
    passivos_sobre_ativos_nao_correntes_venda_descontinuados         = models.FloatField(default=0)
    passivos_sobre_ativos_nao_correntes_venda_descontinuados1        = models.FloatField(default=0)
    passivos_sobre_ativos_nao_correntes_venda_descontinuados2        = models.FloatField(default=0)
    passivos_sobre_ativos_nao_correntes_venda1       = models.FloatField(default=0)
    passivos_sobre_ativos_operacoes_descontinuadas   = models.FloatField(default=0)
    patrimonio_liquido_atribuido_nao_controladores   = models.FloatField(default=0)
    patrimonio_liquido_consolidado   = models.FloatField(default=0)
    patrimonio_liquido_consolidado1  = models.FloatField(default=0)
    provisao_pagamentos_efetuar      = models.FloatField(default=0)
    provisoes        = models.FloatField(default=0)
    provisoes1       = models.FloatField(default=0)
    reservas_capital         = models.FloatField(default=0)
    reservas_capital1        = models.FloatField(default=0)
    reservas_lucros  = models.FloatField(default=0)
    reservas_lucros1         = models.FloatField(default=0)
    reservas_reavaliacao     = models.FloatField(default=0)
    reservas_reavaliacao1    = models.FloatField(default=0)
    tributos_diferidos       = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_balanco_passivo'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMBalancoPassivoIndividual(CVMModelo):
    ajustes_acumulados_conversao     = models.FloatField(default=0)
    ajustes_acumulados_conversao1    = models.FloatField(default=0)
    ajustes_avaliacao_patrimonial    = models.FloatField(default=0)
    ajustes_avaliacao_patrimonial1   = models.FloatField(default=0)
    ajustes_avaliacao_patrimonial2   = models.FloatField(default=0)
    capital_social_realizado         = models.FloatField(default=0)
    capital_social_realizado1        = models.FloatField(default=0)
    capital_social_realizado2        = models.FloatField(default=0)
    correntes        = models.FloatField(default=0)
    despesa_pessoal  = models.FloatField(default=0)
    diferidos        = models.FloatField(default=0)
    diversas         = models.FloatField(default=0)
    dividas_subordinadas     = models.FloatField(default=0)
    emprestimos_financiamentos       = models.FloatField(default=0)
    emprestimos_financiamentos1      = models.FloatField(default=0)
    fiscais_previdenciarias  = models.FloatField(default=0)
    fornecedores     = models.FloatField(default=0)
    instrumentos_financeiros_derivativos     = models.FloatField(default=0)
    instrumentos_financeiros_derivativos1    = models.FloatField(default=0)
    lucros_prejuizos_acumulados      = models.FloatField(default=0)
    lucros_prejuizos_acumulados1     = models.FloatField(default=0)
    lucros_prejuizos_acumulados2     = models.FloatField(default=0)
    lucros_receitas_apropriar        = models.FloatField(default=0)
    negociacao_intermediacao_valores         = models.FloatField(default=0)
    obrigacoes_fiscais       = models.FloatField(default=0)
    obrigacoes_repasse_exterior      = models.FloatField(default=0)
    obrigacoes_repasse_exterior1     = models.FloatField(default=0)
    obrigacoes_repasse_pais  = models.FloatField(default=0)
    obrigacoes_sociais_trabalhistas  = models.FloatField(default=0)
    outras_obrigacoes        = models.FloatField(default=0)
    outras_obrigacoes1       = models.FloatField(default=0)
    outras_obrigacoes2       = models.FloatField(default=0)
    outras_obrigacoes3       = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_passivos  = models.FloatField(default=0)
    outros_resultados_abrangentes    = models.FloatField(default=0)
    outros_resultados_abrangentes1   = models.FloatField(default=0)
    passivo_circulante       = models.FloatField(default=0)
    passivo_nao_circulante   = models.FloatField(default=0)
    passivo_total    = models.FloatField(default=0)
    passivos_fiscais         = models.FloatField(default=0)
    passivos_sobre_ativos_nao_correntes_venda        = models.FloatField(default=0)
    passivos_sobre_ativos_nao_correntes_venda_descontinuados         = models.FloatField(default=0)
    passivos_sobre_ativos_nao_correntes_venda_descontinuados1        = models.FloatField(default=0)
    passivos_sobre_ativos_nao_correntes_venda_descontinuados2        = models.FloatField(default=0)
    passivos_sobre_ativos_operacoes_descontinuadas   = models.FloatField(default=0)
    patrimonio_liquido       = models.FloatField(default=0)
    patrimonio_liquido1      = models.FloatField(default=0)
    provisoes        = models.FloatField(default=0)
    provisoes1       = models.FloatField(default=0)
    reservas_capital         = models.FloatField(default=0)
    reservas_capital1        = models.FloatField(default=0)
    reservas_capital2        = models.FloatField(default=0)
    reservas_lucro   = models.FloatField(default=0)
    reservas_lucros  = models.FloatField(default=0)
    reservas_lucros1         = models.FloatField(default=0)
    reservas_reavaliacao     = models.FloatField(default=0)
    reservas_reavaliacao1    = models.FloatField(default=0)
    reservas_reavaliacao2    = models.FloatField(default=0)
    resultado_exercicios_futuros     = models.FloatField(default=0)
    resultados_exercicios_futuros    = models.FloatField(default=0)
    sociais_estatutarias     = models.FloatField(default=0)
    tributos_diferidos       = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_balanco_passivo_individual'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMFluxoCaixaDireto(CVMModelo):
    adiantamentos_fornecedores_funcionarios  = models.FloatField(default=0)
    agio_subscricao_acoes    = models.FloatField(default=0)
    ajuste_avaliacao_patrimonial_reflexo     = models.FloatField(default=0)
    alienacao_ativo_imobilizado      = models.FloatField(default=0)
    alienacao_ativos_finan_valor_justo_meio_outros_res_abrang        = models.FloatField(default=0)
    alienacao_ativos_financeiros_valor_justo_meio_resultado  = models.FloatField(default=0)
    alienacao_intangivel     = models.FloatField(default=0)
    aquisicao_ativos_finan_valor_justo_meio_outros_res_abrang        = models.FloatField(default=0)
    aquisicao_imobilizado_uso        = models.FloatField(default=0)
    aquisicao_intangivel     = models.FloatField(default=0)
    aquisicao_investimentos  = models.FloatField(default=0)
    aquisicao_liquida_ativo_imobilizado_subsidiarias         = models.FloatField(default=0)
    aquisicao_liquida_intangivel_subsidiarias        = models.FloatField(default=0)
    aumento_capital  = models.FloatField(default=0)
    aumento_reducao_caixa_equivalentes       = models.FloatField(default=0)
    baixa_alienacao_ativo_imobilizado_intangivel     = models.FloatField(default=0)
    caixa_gerado_operacoes   = models.FloatField(default=0)
    caixa_liquido_atividades_financiamento   = models.FloatField(default=0)
    caixa_liquido_atividades_investimento    = models.FloatField(default=0)
    caixa_liquido_atividades_operacionais    = models.FloatField(default=0)
    cancelamento_acoes_tesouraria    = models.FloatField(default=0)
    contas_receber_clientes  = models.FloatField(default=0)
    despesas_antecipadas     = models.FloatField(default=0)
    dividendos_pagos         = models.FloatField(default=0)
    estoques         = models.FloatField(default=0)
    fornecedores     = models.FloatField(default=0)
    imposto_renda_contribuicao_social_diferidos      = models.FloatField(default=0)
    impostos_pagos_sobre_lucro       = models.FloatField(default=0)
    impostos_parcelados      = models.FloatField(default=0)
    impostos_recuperar       = models.FloatField(default=0)
    juros_pagos      = models.FloatField(default=0)
    obrigacoes_sociais_tributarias   = models.FloatField(default=0)
    outras_obrigacoes        = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_creditos  = models.FloatField(default=0)
    outros_investimentos     = models.FloatField(default=0)
    pagamentos_passivos_arrendamentos_ifrs16         = models.FloatField(default=0)
    participacao_acionistas_nao_controladores        = models.FloatField(default=0)
    provisao_contingencias_pcld      = models.FloatField(default=0)
    recebimento_vendas_ativos        = models.FloatField(default=0)
    result_liq_valor_presente_justo_subv_impairment_desc_covid       = models.FloatField(default=0)
    saldo_final_caixa_equivalentes   = models.FloatField(default=0)
    saldo_inicial_caixa_equivalentes         = models.FloatField(default=0)
    titulos_valores_mobiliarios      = models.FloatField(default=0)
    variacao_cambial_caixa_equivalentes      = models.FloatField(default=0)
    variacoes_ativos_passivos        = models.FloatField(default=0)
    venda_recompra_acoes_tesouraria  = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_fluxo_caixa_direto'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMFluxoCaixaDiretoIndividual(CVMModelo):
    adiantamento_futuro_aumento_capital      = models.FloatField(default=0)
    adiantamentos_fornecedores_funcionarios  = models.FloatField(default=0)
    adiantamentos_futuro_aumento_capital_controlada  = models.FloatField(default=0)
    alienacao_controlada_celg_t      = models.FloatField(default=0)
    aquisicao_emprestimos_financiamentos     = models.FloatField(default=0)
    aquisicao_intangivel     = models.FloatField(default=0)
    aquisicao_outros_instrumentos_financeiros        = models.FloatField(default=0)
    aumento_reducao_caixa_equivalentes       = models.FloatField(default=0)
    baixa_alienacao_ativo_imobilizado_intangivel     = models.FloatField(default=0)
    caixa_liquido_atividades_financiamento   = models.FloatField(default=0)
    caixa_liquido_atividades_investimento    = models.FloatField(default=0)
    caixa_liquido_atividades_operacionais    = models.FloatField(default=0)
    contas_receber_clientes  = models.FloatField(default=0)
    depreciacao_amortizacao  = models.FloatField(default=0)
    despesas_antecipadas     = models.FloatField(default=0)
    dividendos_recebidos_controladas         = models.FloatField(default=0)
    entrada_recursos_partes_relacionadas     = models.FloatField(default=0)
    estoques         = models.FloatField(default=0)
    fornecedores     = models.FloatField(default=0)
    imposto_renda_contribuicao_social_diferidos      = models.FloatField(default=0)
    impostos_pagos_sobre_lucro       = models.FloatField(default=0)
    impostos_parcelados      = models.FloatField(default=0)
    impostos_recuperar       = models.FloatField(default=0)
    investimento_reflexo     = models.FloatField(default=0)
    juros_empretimos_financiamentos  = models.FloatField(default=0)
    juros_pagos      = models.FloatField(default=0)
    obrigacoes_tributarias_sociais   = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_creditos  = models.FloatField(default=0)
    outros_investimentos     = models.FloatField(default=0)
    outros_recebimentos      = models.FloatField(default=0)
    outros_resultados_liquidos       = models.FloatField(default=0)
    pagamento_fornecedores   = models.FloatField(default=0)
    pagamento_principal_passivos_arrendamento        = models.FloatField(default=0)
    partes_relacionadas      = models.FloatField(default=0)
    passivos_arrendamento    = models.FloatField(default=0)
    provisao_contingencias_pcld      = models.FloatField(default=0)
    recebimento_dividendos   = models.FloatField(default=0)
    resultado_liq_vlr_presente_emprestimos_direitos_uso      = models.FloatField(default=0)
    saidas_recursos_partes_relacionadas      = models.FloatField(default=0)
    saldo_final_caixa_equivalentes   = models.FloatField(default=0)
    saldo_inicial_caixa_equivalentes         = models.FloatField(default=0)
    titulos_valores_mobiliarios      = models.FloatField(default=0)
    variacao_cambial_caixa_equivalentes      = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_fluxo_caixa_direto_individual'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMFluxoCaixaIndireto(CVMModelo):
    acoes_tesouraria         = models.FloatField(default=0)
    adiantamento_futuro_aumento_capital      = models.FloatField(default=0)
    aplicacoes_financeiras   = models.FloatField(default=0)
    aquis_invest_associadas_entidades_controladas_conjunto   = models.FloatField(default=0)
    aquisicao_imobilizado    = models.FloatField(default=0)
    aquisicao_intangivel     = models.FloatField(default=0)
    aumento_capital  = models.FloatField(default=0)
    aumento_capital_controladas      = models.FloatField(default=0)
    aumento_capital1         = models.FloatField(default=0)
    aumento_capital2         = models.FloatField(default=0)
    aumento_capital3         = models.FloatField(default=0)
    aumento_reducao_caixa_equivalentes       = models.FloatField(default=0)
    caixa_gerado_operacoes   = models.FloatField(default=0)
    caixa_liquido_atividades_financiamento   = models.FloatField(default=0)
    caixa_liquido_atividades_investimento    = models.FloatField(default=0)
    caixa_liquido_atividades_operacionais    = models.FloatField(default=0)
    caixa_liquido_recebido_alienacao_mapfre_bb_sh2   = models.FloatField(default=0)
    captacao_emprestimos_financiamentos      = models.FloatField(default=0)
    compra_acoes_tesouraria  = models.FloatField(default=0)
    dividendos_pagos         = models.FloatField(default=0)
    dividendos_pagos1        = models.FloatField(default=0)
    dividendos_pagos2        = models.FloatField(default=0)
    dividendos_pagos3        = models.FloatField(default=0)
    dividendos_pagos4        = models.FloatField(default=0)
    dividendos_recebidos     = models.FloatField(default=0)
    dividendos_recebidos1    = models.FloatField(default=0)
    dividendos_recebidos2    = models.FloatField(default=0)
    dividendos_recebidos3    = models.FloatField(default=0)
    efeito_variacao_cambial_caixa_investida  = models.FloatField(default=0)
    mutuo_concedido_entre_partes_relacionadas        = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_recebimentos_pagamentos_liquidos  = models.FloatField(default=0)
    outros_recebimentos_pagamentos_liquidos1         = models.FloatField(default=0)
    outros1  = models.FloatField(default=0)
    outros2  = models.FloatField(default=0)
    outros3  = models.FloatField(default=0)
    pagamento_aquisicao_controlada   = models.FloatField(default=0)
    pagamento_derivativos    = models.FloatField(default=0)
    pagamento_juros_sobre_arrendamentos      = models.FloatField(default=0)
    pagamentos_emprestimos_financiamentos    = models.FloatField(default=0)
    partes_relacionadas      = models.FloatField(default=0)
    partes_relacionadas1     = models.FloatField(default=0)
    recebimento_instrumentos_finan_derivativos_exceto_divida         = models.FloatField(default=0)
    saldo_final_caixa_equivalentes   = models.FloatField(default=0)
    saldo_inicial_caixa_equivalentes         = models.FloatField(default=0)
    titulos_valores_mobiliarios      = models.FloatField(default=0)
    transacoes_acionistas_nao_controladores  = models.FloatField(default=0)
    variacao_cambial_caixa_equivalentes      = models.FloatField(default=0)
    variacoes_ativos_passivos        = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_fluxo_caixa_indireto'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMFluxoCaixaIndiretoIndividual(CVMModelo):
    adiantamento_futuro_aumento_capital      = models.FloatField(default=0)
    adiantamento_futuro_aumento_capital1     = models.FloatField(default=0)
    adiantamento_futuro_aumento_capital2     = models.FloatField(default=0)
    alienacao_intangivel     = models.FloatField(default=0)
    amortizacao_debentures   = models.FloatField(default=0)
    amortizacao_passivo_arrendamento         = models.FloatField(default=0)
    aporte_aumento_capital   = models.FloatField(default=0)
    aquisicao_acoes_propria_emissao  = models.FloatField(default=0)
    aquisicao_empresas       = models.FloatField(default=0)
    aquisicao_imobilizado    = models.FloatField(default=0)
    aquisicao_intangivel     = models.FloatField(default=0)
    aumento_capital  = models.FloatField(default=0)
    aumento_capital_controlada       = models.FloatField(default=0)
    aumento_capital_controlada1      = models.FloatField(default=0)
    aumento_capital_subscricao_acao  = models.FloatField(default=0)
    aumento_capital1         = models.FloatField(default=0)
    aumento_capital2         = models.FloatField(default=0)
    aumento_capital3         = models.FloatField(default=0)
    aumento_reducao_caixa_equivalentes       = models.FloatField(default=0)
    caixa_gerado_operacoes   = models.FloatField(default=0)
    caixa_liq_aplicado_gerado_ativ_invest_operacoes_descont  = models.FloatField(default=0)
    caixa_liquido_atividades_financiamento   = models.FloatField(default=0)
    caixa_liquido_atividades_investimento    = models.FloatField(default=0)
    caixa_liquido_atividades_operacionais    = models.FloatField(default=0)
    custos_apropriar_debentures      = models.FloatField(default=0)
    dividendos_juros_sobre_capital_proprio_pagos_acionistas  = models.FloatField(default=0)
    dividendos_pagos         = models.FloatField(default=0)
    dividendos_pagos1        = models.FloatField(default=0)
    dividendos_pagos2        = models.FloatField(default=0)
    dividendos_pagos3        = models.FloatField(default=0)
    dividendos_recebidos     = models.FloatField(default=0)
    dividendos_recebidos1    = models.FloatField(default=0)
    dividendos_recebidos2    = models.FloatField(default=0)
    efeito_liquido_incorporacao      = models.FloatField(default=0)
    gastos_emissao_acoes     = models.FloatField(default=0)
    gastos_emissao_acoes1    = models.FloatField(default=0)
    instrumentos_derivativos_recebidos_liquidos      = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_ajustes   = models.FloatField(default=0)
    outros1  = models.FloatField(default=0)
    outros2  = models.FloatField(default=0)
    outros3  = models.FloatField(default=0)
    pagamento_instrument_financeiros_derivativos_exceto_divida       = models.FloatField(default=0)
    recompra_debenture       = models.FloatField(default=0)
    resgate_acoes_preferenciais      = models.FloatField(default=0)
    saldo_final_caixa_equivalentes   = models.FloatField(default=0)
    saldo_inicial_caixa_equivalentes         = models.FloatField(default=0)
    variacao_cambial_caixa_equivalentes      = models.FloatField(default=0)
    variacoes_ativos_passivos        = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_fluxo_caixa_indireto_individual'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMMutacoesPatrimonioLiquido(CVMModelo):
    absorcao_prejuizo_reserva_futuro_aumento_capital         = models.FloatField(default=0)
    acoes_tesouraria_adquiridas      = models.FloatField(default=0)
    acoes_tesouraria_vendidas        = models.FloatField(default=0)
    adiantamento_futuro_aumento_capital      = models.FloatField(default=0)
    ajustes_exercicios_anteriores    = models.FloatField(default=0)
    ajustes_periodo_anteriores_equivalencia_patrimonial      = models.FloatField(default=0)
    aumento_reducao_patrimonial_reorganizacao_societaria     = models.FloatField(default=0)
    aumentos_capital         = models.FloatField(default=0)
    constituicao_reservas    = models.FloatField(default=0)
    custo_transacao_relacionada_oferta_publica_acoes         = models.FloatField(default=0)
    dividendos       = models.FloatField(default=0)
    dividendos_adicionais_propostos  = models.FloatField(default=0)
    dividendos_nao_controladores     = models.FloatField(default=0)
    dividendos_prescritos    = models.FloatField(default=0)
    dividendos_prescritos_complemento        = models.FloatField(default=0)
    gastos_emissao_acoes     = models.FloatField(default=0)
    juros_sobre_capital_proprio      = models.FloatField(default=0)
    lucro_liquido_periodo    = models.FloatField(default=0)
    movimento_reserva_capital        = models.FloatField(default=0)
    mutacoes_internas_patrimonio_liquido     = models.FloatField(default=0)
    oferta_acoes_empresa_controlada_nota_1_1         = models.FloatField(default=0)
    oferta_publica   = models.FloatField(default=0)
    opcao_venda_controlada   = models.FloatField(default=0)
    opcoes_outorgadas_reconhecidas   = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_efeitos_variacoes_pl_controladas  = models.FloatField(default=0)
    outros_resultados_abrangentes    = models.FloatField(default=0)
    outros_resultados_abrangentes1   = models.FloatField(default=0)
    outros1  = models.FloatField(default=0)
    outros2  = models.FloatField(default=0)
    particip_acion_nao_controladores_patrim_liq_controladas  = models.FloatField(default=0)
    particip_nao_controladores_patrim_liq_decorrente_aquisicao       = models.FloatField(default=0)
    realizacao_reserva_reavaliacao   = models.FloatField(default=0)
    reclassificacoes_resultado       = models.FloatField(default=0)
    recompra_acoes   = models.FloatField(default=0)
    reserva_especial_dividendos      = models.FloatField(default=0)
    reserva_investimento_expansao    = models.FloatField(default=0)
    reserva_legal    = models.FloatField(default=0)
    reserva_legal1   = models.FloatField(default=0)
    resultado_abrangente_total       = models.FloatField(default=0)
    resultado_realizacao_plano_outorga_stock_options         = models.FloatField(default=0)
    saldos_finais    = models.FloatField(default=0)
    saldos_iniciais  = models.FloatField(default=0)
    saldos_iniciais_ajustados        = models.FloatField(default=0)
    transacoes_capital_socios        = models.FloatField(default=0)
    transacoes_nao_contradores       = models.FloatField(default=0)
    transacoes_pagamento_baseados_acoes_liquidavel_acoes     = models.FloatField(default=0)
    transferencia_plano_opcoes_compra        = models.FloatField(default=0)
    tributos_sobre_realizacao_reserva_reavaliacao    = models.FloatField(default=0)
    venda_acoes_tesouraria   = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_mutacoes_patrimonio_liquido'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMMutacoesPatrimonioLiquidoIndividual(CVMModelo):
    acoes_tesouraria         = models.FloatField(default=0)
    acoes_tesouraria_adquiridas      = models.FloatField(default=0)
    acoes_tesouraria_vendidas        = models.FloatField(default=0)
    adocao_inicial_ifrs_09_15_janeiro_2018   = models.FloatField(default=0)
    ajustes_acumulados_conversao     = models.FloatField(default=0)
    ajustes_combinacao_negocios      = models.FloatField(default=0)
    ajustes_exercicios_anteriores    = models.FloatField(default=0)
    ajustes_titulos_valores_mobiliarios      = models.FloatField(default=0)
    aplicacao_inicial_cpc_48         = models.FloatField(default=0)
    aprovacao_dividendos_adicionais_propostos        = models.FloatField(default=0)
    aumento_capital  = models.FloatField(default=0)
    aumento_reducao_capital_social   = models.FloatField(default=0)
    aumento_reducao_patrimonial_reorganizacao_societaria     = models.FloatField(default=0)
    aumento_reducao_patrimonial_reorganizacao_societaria1    = models.FloatField(default=0)
    aumentos_capital         = models.FloatField(default=0)
    cancelamento_acoes_rca   = models.FloatField(default=0)
    cisao    = models.FloatField(default=0)
    complemento_dividendos_minimos_obrigatorios      = models.FloatField(default=0)
    constituicao_realizacao_reservas_capital         = models.FloatField(default=0)
    constituicao_reservas    = models.FloatField(default=0)
    correcao_monetaria_hiperinflacao         = models.FloatField(default=0)
    custo_emissao_acoes      = models.FloatField(default=0)
    custos_oferta_publica_primaria   = models.FloatField(default=0)
    dividendo_adicional_proposto     = models.FloatField(default=0)
    dividendos       = models.FloatField(default=0)
    dividendos_adicionais_propostos  = models.FloatField(default=0)
    dividendos_declarados    = models.FloatField(default=0)
    dividendos_intermediarios        = models.FloatField(default=0)
    dividendos_jscp_prescritos       = models.FloatField(default=0)
    dividendos_juros_sobre_capital_proprio_prescritos        = models.FloatField(default=0)
    dividendos_juros_sobre_capital_proprio_prescritos1       = models.FloatField(default=0)
    dividendos_juros_sobre_capital_proprio_prescritos2       = models.FloatField(default=0)
    dividendos_minimos_obrigatorios  = models.FloatField(default=0)
    dividendos_propostos_reservas    = models.FloatField(default=0)
    dividendos1      = models.FloatField(default=0)
    efeito_fiscal    = models.FloatField(default=0)
    efeitos_tribut_sobre_realizacao_oscilac_cambial_invest_ext       = models.FloatField(default=0)
    ganho_capital_acoes_tesouraria   = models.FloatField(default=0)
    ganho_capital_reserva_estatutaria        = models.FloatField(default=0)
    garantias_financeiras_prestadas_resolucao_cmn_4_512      = models.FloatField(default=0)
    gastos_emissao_acoes     = models.FloatField(default=0)
    hedge_investimentos_exterior     = models.FloatField(default=0)
    juros_sobre_capital_proprio      = models.FloatField(default=0)
    juros_sobre_capital_proprio_declarados_apos_2019         = models.FloatField(default=0)
    lucro_liquido_periodo    = models.FloatField(default=0)
    lucro_liquido_periodo1   = models.FloatField(default=0)
    lucro_liquido_periodo2   = models.FloatField(default=0)
    mutacoes_internas_patrimonio_liquido     = models.FloatField(default=0)
    opcoes_outorgadas_reconhecidas   = models.FloatField(default=0)
    outras_transacoes_capital        = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_resultados_abrangentes    = models.FloatField(default=0)
    outros1  = models.FloatField(default=0)
    plano_beneficios_funcionarios    = models.FloatField(default=0)
    realizacao_oscilacao_cambial_investimento_exterior       = models.FloatField(default=0)
    realizacao_reserva_reavaliacao   = models.FloatField(default=0)
    realizacao_reserva_reavaliacao1  = models.FloatField(default=0)
    reclassificacao_conforme_cpc_33  = models.FloatField(default=0)
    reclassificacoes_resultado       = models.FloatField(default=0)
    recompra_acoes   = models.FloatField(default=0)
    reconhecimento_planos_pagamento_baseado_acoes    = models.FloatField(default=0)
    remensuracoes_obrigacoes_beneficios_pos_emprego  = models.FloatField(default=0)
    reserva_especial_dividendos      = models.FloatField(default=0)
    reserva_incentivo_fiscal         = models.FloatField(default=0)
    reserva_incentivo_fiscal_sudene  = models.FloatField(default=0)
    reserva_legal    = models.FloatField(default=0)
    reserva_retencao_lucros  = models.FloatField(default=0)
    reservas_pagamento_baseado_acoes         = models.FloatField(default=0)
    reservas_pagamento_baseado_acoes1        = models.FloatField(default=0)
    resultado_abrangente_total       = models.FloatField(default=0)
    reversao_dividendos_prescritos   = models.FloatField(default=0)
    saldo_final      = models.FloatField(default=0)
    saldos_finais    = models.FloatField(default=0)
    saldos_iniciais  = models.FloatField(default=0)
    saldos_iniciais_ajustados        = models.FloatField(default=0)
    transacoes_capital       = models.FloatField(default=0)
    transacoes_capital_socios        = models.FloatField(default=0)
    tributos_sobre_realizacao_reserva_reavaliacao    = models.FloatField(default=0)
    variacao_participacao_investimentos_minoritarios         = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_mutacoes_patrimonio_liquido_individual'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMResultado(CVMModelo):
    ajuste_expect_fluxo_caixa_ativo_finan_inden_conces_distrib       = models.FloatField(default=0)
    atribuido_socios_empresa_controladora    = models.FloatField(default=0)
    atribuido_socios_empresa_controladora1   = models.FloatField(default=0)
    atribuido_socios_empresa_controladora2   = models.FloatField(default=0)
    atribuido_socios_nao_controladores       = models.FloatField(default=0)
    atribuido_socios_nao_controladores1      = models.FloatField(default=0)
    atribuido_socios_nao_controladores2      = models.FloatField(default=0)
    compensacao_financeira_utilizacao_recursos_hidricos_cfurh        = models.FloatField(default=0)
    corrente         = models.FloatField(default=0)
    custo_bens_ou_servicos_vendidos  = models.FloatField(default=0)
    custo_construcao         = models.FloatField(default=0)
    custo_construcao1        = models.FloatField(default=0)
    custo_mercadorias_produtos_vendidos      = models.FloatField(default=0)
    custo_servicos_terceiros         = models.FloatField(default=0)
    depreciacao_amortizacao  = models.FloatField(default=0)
    despesas_administrativas         = models.FloatField(default=0)
    despesas_financeiras     = models.FloatField(default=0)
    despesas_gerais_administrativas  = models.FloatField(default=0)
    despesas_imoveis_destinados_renda_venda  = models.FloatField(default=0)
    despesas_juros_similares         = models.FloatField(default=0)
    despesas_pessoal         = models.FloatField(default=0)
    despesas_receitas_operacionais   = models.FloatField(default=0)
    despesas_tributos        = models.FloatField(default=0)
    despesas_vendas  = models.FloatField(default=0)
    diferido         = models.FloatField(default=0)
    ganhos_perdas_liq_sobre_ativos_operacoes_descontinuadas1         = models.FloatField(default=0)
    ganhos_perdas_liquidas_sobre_ativos_operacoes_descont    = models.FloatField(default=0)
    imposto_renda_contribuicao_social_sobre_lucro    = models.FloatField(default=0)
    liquidacao_ccee  = models.FloatField(default=0)
    lucro_acao_reais_acao    = models.FloatField(default=0)
    lucro_basico_acao        = models.FloatField(default=0)
    lucro_diluido_acao       = models.FloatField(default=0)
    lucro_acao        = models.FloatField(default=0)
    lucro_acao1        = models.FloatField(default=0)
    lucro_prejuizo_consolidado_periodo       = models.FloatField(default=0)
    lucro_prejuizo_consolidado_periodo1      = models.FloatField(default=0)
    lucro_prejuizo_liquido_operacoes_descontinuadas  = models.FloatField(default=0)
    lucro_prejuizo_liquido_operacoes_descontinuadas1         = models.FloatField(default=0)
    material         = models.FloatField(default=0)
    operacoes_capitalizacao  = models.FloatField(default=0)
    operacoes_capitalizacao1         = models.FloatField(default=0)
    operacoes_previdencia_complementar       = models.FloatField(default=0)
    operacoes_previdencia_complementar1      = models.FloatField(default=0)
    operacoes_resseguros     = models.FloatField(default=0)
    operacoes_resseguros1    = models.FloatField(default=0)
    operacoes_seguros        = models.FloatField(default=0)
    outras_despesas_operacionais     = models.FloatField(default=0)
    outras_despesas_operacionais1    = models.FloatField(default=0)
    outras_receitas  = models.FloatField(default=0)
    outras_receitas_despesas         = models.FloatField(default=0)
    outras_receitas_operacionais     = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_custos    = models.FloatField(default=0)
    outros_encargos  = models.FloatField(default=0)
    perdas_esperadas_ativos_financeiros_operacoes_credito    = models.FloatField(default=0)
    perdas_nao_recuperabilidade_ativos       = models.FloatField(default=0)
    provisoes_operacionais   = models.FloatField(default=0)
    receita_antecipacao_prestacao_servico    = models.FloatField(default=0)
    receita_atualizacao_financeira_bonificacao_outorga       = models.FloatField(default=0)
    receita_venda_bens_ou_servicos   = models.FloatField(default=0)
    receitas_comissoes_liquidas      = models.FloatField(default=0)
    receitas_financeiras     = models.FloatField(default=0)
    remuneracao_financeira_ativo_contrato_transmissao        = models.FloatField(default=0)
    resultado_antes_resultado_financeiro_tributos    = models.FloatField(default=0)
    resultado_antes_tributos_sobre_lucro     = models.FloatField(default=0)
    resultado_bruto  = models.FloatField(default=0)
    resultado_equivalencia_patrimonial       = models.FloatField(default=0)
    resultado_equivalencia_patrimonial1      = models.FloatField(default=0)
    resultado_financeiro     = models.FloatField(default=0)
    resultado_liquido_operacoes_continuadas  = models.FloatField(default=0)
    resultado_liquido_operacoes_descontinuadas       = models.FloatField(default=0)
    resultado_liquido_operacoes_descontinuadas1      = models.FloatField(default=0)
    resultado_revisao_tarifaria_periodica_contrato_transmissao       = models.FloatField(default=0)
    seguros  = models.FloatField(default=0)
    servicos_terceiros       = models.FloatField(default=0)
    transacoes_mecanismo_venda_excedentes_mve        = models.FloatField(default=0)
    tributos         = models.FloatField(default=0)
    variacao_provisoes_tecnicas_seguros      = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_resultado'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMResultadoAbrangente(CVMModelo):
    atribuido_socios_empresa_controladora    = models.FloatField(default=0)
    atribuido_socios_empresa_controladora1   = models.FloatField(default=0)
    atribuido_socios_empresa_nao_controladora        = models.FloatField(default=0)
    atribuido_socios_nao_controladores       = models.FloatField(default=0)
    efeito_cambial_economia_hiperinflacionaria       = models.FloatField(default=0)
    efeitos_triutarios_sobre_perda_atuarial  = models.FloatField(default=0)
    equiv_sobre_efeitos_tribut_ganho_perda_op_hedge_fluxo_caixa      = models.FloatField(default=0)
    equivalencia_sobre_efeitos_tributarios_sobre_perda_atuarial      = models.FloatField(default=0)
    equivalencia_sobre_ganho_perda_atuarial  = models.FloatField(default=0)
    ganho_perda_atuarial     = models.FloatField(default=0)
    imposto_renda_contribuicao_social_diferidos      = models.FloatField(default=0)
    lucro_liquido_consolidado_periodo        = models.FloatField(default=0)
    opcao_recompra_participacao_acionaria    = models.FloatField(default=0)
    outros_resultados_abrangentes    = models.FloatField(default=0)
    perdas_nao_realizadas_reavaliacao_saldos_entre_empresas  = models.FloatField(default=0)
    plano_incentivo_longo_prazo_liquido_impostos     = models.FloatField(default=0)
    resultado_abrangente_consolidado_periodo         = models.FloatField(default=0)
    resultado_abrangente_periodo     = models.FloatField(default=0)
    valores_nao_serao_reclassificados_resultado      = models.FloatField(default=0)
    valores_serao_reclassificados_resultado  = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_resultado_abrangente'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMResultadoAbrangenteIndividual(CVMModelo):
    conversao_demonstracoes_financeiras_controladas_exterior         = models.FloatField(default=0)
    efeito_cambial_economia_hiperinflacionaria       = models.FloatField(default=0)
    efeitos_triutarios_sobre_perda_atuarial  = models.FloatField(default=0)
    equivalencia_sobre_efeitos_tributarios_sobre_perda_atuarial      = models.FloatField(default=0)
    equivalencia_sobre_ganho_perda_atuarial  = models.FloatField(default=0)
    ganhos_atuariais_plano_beneficio_definido_liq_impostos1  = models.FloatField(default=0)
    ganhos_atuariais_plano_beneficio_definido_liquidas_impostos      = models.FloatField(default=0)
    hedge_fluxo_caixa        = models.FloatField(default=0)
    lucro_abrangente         = models.FloatField(default=0)
    lucro_abrangente_part_nao_controladores  = models.FloatField(default=0)
    lucro_liquido_periodo    = models.FloatField(default=0)
    lucro_ou_prejuizo_liquido_periodo        = models.FloatField(default=0)
    outros_resultados_abrangentes    = models.FloatField(default=0)
    perdas_nao_realizadas_reavaliacao_saldos_entre_empresas  = models.FloatField(default=0)
    resultado_abrangente_periodo     = models.FloatField(default=0)
    resultado_abrangente_periodo1    = models.FloatField(default=0)
    transferencias_impactos_realizados_lucro_liquido         = models.FloatField(default=0)
    tributos_diferidos_sobre_resultados_abrangentes  = models.FloatField(default=0)
    tributos_diferidos_sobre_resultados_abrangentes1         = models.FloatField(default=0)
    valores_nao_serao_reclassificados_resultado      = models.FloatField(default=0)
    valores_nao_serao_reclassificados_resultado1     = models.FloatField(default=0)
    valores_serao_reclassificados_resultado  = models.FloatField(default=0)
    valores_serao_reclassificados_resultado1         = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_resultado_abrangente_individual'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMResultadoIndividual(CVMModelo):
    amortizacao_depreciacao  = models.FloatField(default=0)
    ativo_fiscal_diferido    = models.FloatField(default=0)
    ativo_fiscal_diferido_cs         = models.FloatField(default=0)
    ativo_fiscal_diferido_ir         = models.FloatField(default=0)
    compensacao_financeira_utilizacao_recursos_hidricos_cfurh        = models.FloatField(default=0)
    compensacao_financeira_utilizacao_recursos_hidricos_cfurh1       = models.FloatField(default=0)
    conta_desenvolvimento_energetico_cde     = models.FloatField(default=0)
    contribuicao_social      = models.FloatField(default=0)
    corrente         = models.FloatField(default=0)
    custo_bens_ou_servicos_vendidos  = models.FloatField(default=0)
    custo_servicos_prestados_terceiros       = models.FloatField(default=0)
    custos_operacao  = models.FloatField(default=0)
    despesas_financeiras     = models.FloatField(default=0)
    despesas_gerais_administrativas  = models.FloatField(default=0)
    despesas_pessoal         = models.FloatField(default=0)
    despesas_receitas_operacionais   = models.FloatField(default=0)
    despesas_tributos        = models.FloatField(default=0)
    despesas_vendas  = models.FloatField(default=0)
    diferido         = models.FloatField(default=0)
    empregados       = models.FloatField(default=0)
    encargos_consumidor_mme_fndct_pee        = models.FloatField(default=0)
    ganhos_perdas_liq_sobre_ativos_operacoes_descontinuadas  = models.FloatField(default=0)
    ganhos_perdas_liquidas_sobre_ativos_operacoes_descont1   = models.FloatField(default=0)
    imposto_renda    = models.FloatField(default=0)
    imposto_renda_contribuicao_social_sobre_lucro    = models.FloatField(default=0)
    iss      = models.FloatField(default=0)
    lucro_acao_reais_acao    = models.FloatField(default=0)
    lucro_basico_acao        = models.FloatField(default=0)
    lucro_diluido_acao       = models.FloatField(default=0)
    lucro_prejuizo_liquido_operacoes_descontinuadas  = models.FloatField(default=0)
    lucro_prejuizo_liquido_operacoes_descontinuadas1         = models.FloatField(default=0)
    lucro_prejuizo_periodo   = models.FloatField(default=0)
    lucro_prejuizo_periodo1  = models.FloatField(default=0)
    material         = models.FloatField(default=0)
    operacoes_capitalizacao  = models.FloatField(default=0)
    operacoes_captacao_mercado       = models.FloatField(default=0)
    operacoes_credito        = models.FloatField(default=0)
    operacoes_emprestimos_repasses   = models.FloatField(default=0)
    outras   = models.FloatField(default=0)
    outras_despesas_operacionais     = models.FloatField(default=0)
    outras_despesas_operacionais1    = models.FloatField(default=0)
    outras_receitas_despesas         = models.FloatField(default=0)
    outras_receitas_operacionais     = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros_encargos  = models.FloatField(default=0)
    outros_investimentos     = models.FloatField(default=0)
    outros1  = models.FloatField(default=0)
    outros2  = models.FloatField(default=0)
    perdas_nao_recuperabilidade_ativos       = models.FloatField(default=0)
    pis_cofins       = models.FloatField(default=0)
    provisao_cs_valores_diferidos    = models.FloatField(default=0)
    provisao_perdas_esperadas_creditos_liquidacao_duvidosa   = models.FloatField(default=0)
    receita_venda_bens_ou_servicos   = models.FloatField(default=0)
    receitas_financeiras     = models.FloatField(default=0)
    receitas_juros_instrumento_financeiros   = models.FloatField(default=0)
    resultado_antes_resultado_financeiro_tributos    = models.FloatField(default=0)
    resultado_antes_tributos_sobre_lucro     = models.FloatField(default=0)
    resultado_aplicacoes_compulsorias        = models.FloatField(default=0)
    resultado_bruto  = models.FloatField(default=0)
    resultado_equivalencia_patrimonial       = models.FloatField(default=0)
    resultado_equivalencia_patrimonial1      = models.FloatField(default=0)
    resultado_financeiro     = models.FloatField(default=0)
    resultado_liquido_operacoes_continuadas  = models.FloatField(default=0)
    resultado_liquido_operacoes_descontinuadas       = models.FloatField(default=0)
    resultado_liquido_operacoes_descontinuadas1      = models.FloatField(default=0)
    resultado_operacoes_cambio       = models.FloatField(default=0)
    resultado_operacoes_cambio1      = models.FloatField(default=0)
    resultado_operacoes_titulos_valores_mobiliarios  = models.FloatField(default=0)
    resultado_operacoes_titulos_valores_mobiliarios1         = models.FloatField(default=0)
    resultado_outros_ativos_financeiros      = models.FloatField(default=0)
    servicos_terceiros       = models.FloatField(default=0)
    taxa_fiscalizacao_servicos_energia_eletrica_tfse         = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_resultado_individual'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMValorAdicionado(CVMModelo):
    custos_prods_mercs_servs_vendidos        = models.FloatField(default=0)
    depreciacao_amortizacao_exaustao         = models.FloatField(default=0)
    depreciacao_amortizacao_exaustao1        = models.FloatField(default=0)
    despesas_beneficios_resgates     = models.FloatField(default=0)
    distribuicao_valor_adicionado    = models.FloatField(default=0)
    distribuicao_valor_adicionado1   = models.FloatField(default=0)
    distribuicao_valor_adicionado2   = models.FloatField(default=0)
    impostos_taxas_contribuicoes     = models.FloatField(default=0)
    impostos_taxas_contribuicoes1    = models.FloatField(default=0)
    impostos_taxas_contribuicoes2    = models.FloatField(default=0)
    insumos_adquiridos_terceiros     = models.FloatField(default=0)
    materiais_energia_outros         = models.FloatField(default=0)
    materiais_energia_servs_terceiros_outros         = models.FloatField(default=0)
    outras   = models.FloatField(default=0)
    outras_receitas  = models.FloatField(default=0)
    outras1  = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros1  = models.FloatField(default=0)
    outros2  = models.FloatField(default=0)
    outros3  = models.FloatField(default=0)
    outros4  = models.FloatField(default=0)
    outros5  = models.FloatField(default=0)
    outros6  = models.FloatField(default=0)
    outros7  = models.FloatField(default=0)
    outros8  = models.FloatField(default=0)
    perda_recuperacao_valores_ativos         = models.FloatField(default=0)
    perda_recuperacao_valores_ativos1        = models.FloatField(default=0)
    perda_recuperacao_valores_ativos2        = models.FloatField(default=0)
    pessoal  = models.FloatField(default=0)
    pessoal1         = models.FloatField(default=0)
    pessoal2         = models.FloatField(default=0)
    provisao_reversao_creds_liquidacao_duvidosa      = models.FloatField(default=0)
    provisao_reversao_creds_liquidacao_duvidosa1     = models.FloatField(default=0)
    receitas         = models.FloatField(default=0)
    receitas_financeiras     = models.FloatField(default=0)
    receitas_refs_construcao_ativos_proprios         = models.FloatField(default=0)
    remuneracao_capitais_proprios    = models.FloatField(default=0)
    remuneracao_capitais_proprios1   = models.FloatField(default=0)
    remuneracao_capitais_proprios2   = models.FloatField(default=0)
    remuneracao_capitais_terceiros   = models.FloatField(default=0)
    remuneracao_capitais_terceiros1  = models.FloatField(default=0)
    remuneracao_capitais_terceiros2  = models.FloatField(default=0)
    resultado_equivalencia_patrimonial       = models.FloatField(default=0)
    resultado_equivalencia_patrimonial1      = models.FloatField(default=0)
    retencoes        = models.FloatField(default=0)
    servicos_terceiros       = models.FloatField(default=0)
    valor_adicionado_bruto   = models.FloatField(default=0)
    valor_adicionado_liquido_produzido       = models.FloatField(default=0)
    valor_adicionado_total_distribuir        = models.FloatField(default=0)
    valor_adicionado_total_distribuir1       = models.FloatField(default=0)
    var_despesas_comercializacao_diferidas   = models.FloatField(default=0)
    var_prov_evento_ocorrido_nao_avisado     = models.FloatField(default=0)
    vendas_mercadorias_produtos_servicos     = models.FloatField(default=0)
    vlr_adicionado_recebido_transferencia    = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_valor_adicionado'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]

class CVMValorAdicionadoIndividual(CVMModelo):
    custos_prods_mercs_servs_vendidos        = models.FloatField(default=0)
    depreciacao_amortizacao_exaustao         = models.FloatField(default=0)
    depreciacao_amortizacao_exaustao1        = models.FloatField(default=0)
    despesas_beneficios_resgates     = models.FloatField(default=0)
    distribuicao_valor_adicionado    = models.FloatField(default=0)
    distribuicao_valor_adicionado1   = models.FloatField(default=0)
    distribuicao_valor_adicionado2   = models.FloatField(default=0)
    impostos_taxas_contribuicoes     = models.FloatField(default=0)
    impostos_taxas_contribuicoes1    = models.FloatField(default=0)
    impostos_taxas_contribuicoes2    = models.FloatField(default=0)
    insumos_adquiridos_terceiros     = models.FloatField(default=0)
    materiais_energia_outros         = models.FloatField(default=0)
    materiais_energia_servs_terceiros_outros         = models.FloatField(default=0)
    outras   = models.FloatField(default=0)
    outras_receitas  = models.FloatField(default=0)
    outras1  = models.FloatField(default=0)
    outros   = models.FloatField(default=0)
    outros1  = models.FloatField(default=0)
    outros2  = models.FloatField(default=0)
    outros3  = models.FloatField(default=0)
    outros4  = models.FloatField(default=0)
    outros5  = models.FloatField(default=0)
    outros6  = models.FloatField(default=0)
    outros7  = models.FloatField(default=0)
    outros8  = models.FloatField(default=0)
    perda_recuperacao_valores_ativos         = models.FloatField(default=0)
    perda_recuperacao_valores_ativos1        = models.FloatField(default=0)
    perda_recuperacao_valores_ativos2        = models.FloatField(default=0)
    pessoal  = models.FloatField(default=0)
    pessoal1         = models.FloatField(default=0)
    pessoal2         = models.FloatField(default=0)
    provisao_reversao_creds_liquidacao_duvidosa      = models.FloatField(default=0)
    provisao_reversao_creds_liquidacao_duvidosa1     = models.FloatField(default=0)
    receitas         = models.FloatField(default=0)
    receitas_financeiras     = models.FloatField(default=0)
    receitas_refs_construcao_ativos_proprios         = models.FloatField(default=0)
    remuneracao_capitais_proprios    = models.FloatField(default=0)
    remuneracao_capitais_proprios1   = models.FloatField(default=0)
    remuneracao_capitais_terceiros   = models.FloatField(default=0)
    remuneracao_capitais_terceiros1  = models.FloatField(default=0)
    remuneracao_capital_proprio      = models.FloatField(default=0)
    remuneracao_capital_terceiros    = models.FloatField(default=0)
    resultado_equivalencia_patrimonial       = models.FloatField(default=0)
    resultado_equivalencia_patrimonial1      = models.FloatField(default=0)
    retencoes        = models.FloatField(default=0)
    servicos_terceiros       = models.FloatField(default=0)
    valor_adicionado_bruto   = models.FloatField(default=0)
    valor_adicionado_liquido_produzido       = models.FloatField(default=0)
    valor_adicionado_total_distribuir        = models.FloatField(default=0)
    valor_adicionado_total_distribuir1       = models.FloatField(default=0)
    var_despesas_comercializacao_diferidas   = models.FloatField(default=0)
    var_prov_evento_ocorrido_nao_avisado     = models.FloatField(default=0)
    vendas_mercadorias_produtos_servicos     = models.FloatField(default=0)
    vlr_adicionado_recebido_transferencia    = models.FloatField(default=0)

    class Meta:
        db_table = 'home_cvm_valor_adicionado_individual'
        unique_together = [['empresa','data_inicio_exercicio','data_fim_exercicio']]
        
class MenuItem(models.Model):
    pai = models.ForeignKey('MenuItem', on_delete=models.CASCADE,db_index=True, null=True)
    id  = models.CharField(max_length=40,primary_key=True)       # string;
    ordem = models.IntegerField(default=0)
    nome_configuracao = models.CharField(max_length=20, null=True)
    type  = models.CharField(max_length=20)                                     # string;
    icon   = models.CharField(max_length=30, null=True)                         # GenericCardProps['iconPrimary'];
    title = models.CharField(max_length=40)                                     # ReactNode | string;
    caption = models.CharField(max_length=40, null=True)                        # ReactNode | string;
    color = models.CharField(max_length=20, null=True)                          # 'primary' | 'secondary' | 'default' | undefined;
    target = models.BooleanField(default=False, null=True)
    external = models.CharField(max_length=40, null=True)
    url = models.CharField(max_length=60, null=True)                             # string | undefined;
    breadcrumbs = models.BooleanField(default=False, null=True)
    # disabled = models.BooleanField(default=False)
    # chip?: ChipProps;        

    class Meta:
        db_table = 'home_menu_item'
        ordering = ['ordem', 'title']


