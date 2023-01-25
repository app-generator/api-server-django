from django.forms import CheckboxSelectMultiple, ModelForm, CheckboxInput, DateInput, Select, DateField, IntegerField, MultipleChoiceField
from django.forms import ModelChoiceField, ModelMultipleChoiceField, SelectMultiple, DateTimeField, Textarea, TextInput, CheckboxInput
from django.forms import Widget,SelectMultiple, ModelChoiceField, HiddenInput, NumberInput
from django.forms.models import ModelChoiceIterator
from home.models import Profile, Ranking, ProfileRanking, Plano
# ,ProjecaoAcao
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F
chkClass = {'class': 'form-check-input'}

class RankingChoiceIterator(ModelChoiceIterator):
    def __init__(self, field: ModelChoiceField):
        super().__init__(field)

    def __iter__(self): # -> Iterator[Tuple[Union[int, str], str]]:
        # for i, choice in enumerate(self.choices):
        #     yield ModelChoiceIteratorValue(choice, i)        
        return super().__iter__()

class RankingModelMultipleChoiceField(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.ranking.nome

    def widget_attrs(self, widget: Widget):
        widget.attrs = {'class': 'form-check'}
        return super().widget_attrs(widget)
    
    # def formfield(self, **kwargs):
    #     # This is a fairly standard way to set up some defaults
    #     # while letting the caller override them.
    #     # defaults = {'form_class': MyFormField}
    #     # defaults.update(kwargs)
    #     return super().formfield(**kwargs)

class RankingSelectMultiple(CheckboxSelectMultiple):
    def __init__(self) -> None:
        super().__init__()     

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        selected = value.instance.pranking_visivel
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option['attrs']['class'] = 'form-check-input'
        return option

class FiltroForm(ModelForm):
    frmCtrlClass = {'class': 'form-control'}
    projecao_periodo_inicio = DateField(required=False,label='Início')
    projecao_periodo_inicio.widget.attrs = frmCtrlClass
    projecao_periodo_fim = DateField(required=False,label='Fim')
    projecao_periodo_fim.widget.attrs = frmCtrlClass
    projecao_ultimas = IntegerField(required=False,label='Últimas')
    projecao_ultimas.widget.attrs = frmCtrlClass
    ranking_rankeados = IntegerField(required=False,label='Rankeados')
    ranking_rankeados.widget.attrs = frmCtrlClass
    pranking_visivel = RankingModelMultipleChoiceField(queryset=None)    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alterou_ranking = False
        nr = kwargs['instance'].profileranking_set.filter(ranking__visivel=False).delete()
        for r in Ranking.objects.filter(visivel=True):
            if not kwargs['instance'].profileranking_set.filter(ranking=r).exists():
                ProfileRanking(ranking=r, profile=kwargs['instance']).save()   
        self.fields['pranking_visivel'] = RankingModelMultipleChoiceField(
            queryset=kwargs['instance'].profileranking_set.all().order_by('ranking__ordem'),
            label='',
            widget=RankingSelectMultiple,
        ) 
        self.fields['pranking_visivel'].iterator=RankingChoiceIterator(self.fields['pranking_visivel'])
        ce = ['menu_esconder_inativos','projecao_smallcap']
        if self.instance.plano.desabilitar_configuracao:
            [setattr(self.fields[f],'disabled',True) for f in self.fields if not f in ce]

    def clean(self):
        if super().clean().get("projecao_tipo") in ['u','n']:
            ps = ["projecao_periodo_inicio","projecao_periodo_fim"]
            [self.errors.pop(p) for p in ps if self.errors.get(p)]
            [self.changed_data.remove(p) for p in ps if self.errors.get(p)]

    # def is_valid(self):
    #     v = super().is_valid()
    #     return v

    def has_changed(self):
        c = super().has_changed()
        self.alterou_ranking = False
        if 'pranking_visivel' in self.changed_data:
            lista = [int(k) for k in self.data.getlist('pranking_visivel')]
            self.alterou_ranking = self.instance.profileranking_set.filter((Q(id__in=lista)&Q(pranking_visivel=False))|(~Q(id__in=lista)&Q(pranking_visivel=True))).exists()
        return self.alterou_ranking if self.changed_data == ['pranking_visivel'] else c

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if 'pranking_visivel' in self.changed_data:
            lista = [int(k) for k in self.data.getlist('pranking_visivel')]
            self.instance.profileranking_set.filter(id__in=lista).update(pranking_visivel=True)
            self.instance.profileranking_set.filter(~Q(id__in=lista)).update(pranking_visivel = False)
            ProfileRanking.objects.bulk_update(self.instance.profileranking_set.all(),['pranking_visivel']) 

    class Meta:
        model = Profile
        fields = ('projecao_smallcap','menu_acao', 'menu_empresa', 'menu_setor', 'menu_projecao', 'menu_favorito', 'menu_esconder_inativos', 'projecao_tipo', 'projecao_ultimas', 'projecao_periodo_inicio', 'projecao_periodo_fim', 'pranking_visivel', 'ranking_rankeados')
        labels = {
                'projecao_smallcap': _('Smallcaps'),
                'menu_acao': _('Ações'),
                'menu_empresa': _('Empresas'),
                'menu_setor': _('Setores'),
                'menu_projecao': _('Projeções'),
                'menu_favorito': _('Favoritos'),
                'menu_esconder_inativos': _('Esconder Inativos'),
                'projecao_tipo': _('Restringir'),
        }
        widgets = {
                'projecao_smallcap': CheckboxInput(attrs={'class': 'form-check-input mt-2'}),
                'menu_acao': CheckboxInput(attrs=chkClass),
                'menu_empresa': CheckboxInput(attrs=chkClass),
                'menu_setor': CheckboxInput(attrs=chkClass),
                'menu_projecao': CheckboxInput(attrs=chkClass),
                'menu_favorito': CheckboxInput(attrs=chkClass),
                'menu_esconder_inativos': CheckboxInput(attrs=chkClass),
                'projecao_tipo': Select(attrs={'class':'form-select-sm col-sm-12'}),
        }
        # help_texts = {
        #             'name': _('Some useful help text.'),
        # }
        # error_messages = {
        #     'name': {
        #         'max_length': _("This writer's name is too long."),
        #     },
        # }

class ProfilePlanoForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.planos = Plano.objects.all()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        ce = ['menu_esconder_inativos','projecao_smallcap']
        p = Profile.objects.get(user__username=self.instance.plano.id)
        [setattr(self.instance,c.attname,getattr(p,c.attname)) for c in p._meta.fields if not c.is_relation and not c.attname in ce and not 'id' in c.attname]
        self.instance.save()
        for pr in p.profileranking_set.all():
            try:
                prs = self.instance.profileranking_set.get(ranking=pr.ranking)    
                prs.pranking_visivel = pr.pranking_visivel
                prs.save()
            except:
                print('Erro')

    class Meta:
        model = Profile
        fields = ('plano',)
        labels = {
                'plano': _('Plano'),
        }
        widgets = {
                'plano': HiddenInput(),
        }