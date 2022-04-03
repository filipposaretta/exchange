from django import forms
from .models import Trans

class Buy(forms.ModelForm):

    class Meta:
        model = Trans
        fields = ('buy','one_B_dollar',)
        labels = {
            'buy': 'Inserisci il numero di  Bitcoin che vuoi acquistare',
            'one_B_dollar': 'Inserisci il prezzo di 1 Bitcoin'
        }

class Sell(forms.ModelForm):

    class Meta:
        model = Trans
        fields = ('sell','one_B_dollar',)
        labels = {
            'sell': 'Inserisci il numero di  Bitcoin che vuoi vendere',
            'one_B_dollar': 'Inserisci il prezzo di 1 Bitcoin'
        }