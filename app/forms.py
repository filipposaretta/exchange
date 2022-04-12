from django import forms
from .models import Trans


class Buy(forms.ModelForm):  # acquisto

    class Meta:
        model = Trans
        fields = ('buy','price_1B_in',)
        labels = {
            'buy': 'Inserisci il numero di  Bitcoin che vuoi acquistare',
            'price_1B_in': 'Inserisci il prezzo di 1 Bitcoin'
        }


class Sell(forms.ModelForm): # vendita

    class Meta:
        model = Trans
        fields = ('sell','price_1B_in',)
        labels = {
            'sell': 'Inserisci il numero di  Bitcoin che vuoi vendere',
            'price_1B_in': 'Inserisci il prezzo di 1 Bitcoin'
        }
