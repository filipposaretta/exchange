from django.contrib.auth.models import User
from djongo.models.fields import ObjectIdField
from django.utils import timezone
from djongo import models


class Wallet(models.Model):
    _id = ObjectIdField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    username = models.TextField(max_length=50, default='')
    datetime = models.DateTimeField(auto_now_add=True)
    bitcoin = models.FloatField(default=0)
    dollars = models.FloatField(default=0)
    bitcoin_init = models.FloatField(default=0)
    dollars_init = models.FloatField(default=0)


class Trans(models.Model):  # transazione
    _id = ObjectIdField()
    price_1B_in = models.FloatField(default=0)  # prezzo iniziale di 1 Bitcoin
    creator = models.TextField(max_length=50, default='')
    buy = models.FloatField(default=0)  # bitcoin che rimangono
    sell = models.FloatField(default=0)  # bitcoin che rimangono
    buy_in = models.FloatField(default=0) # iniziali
    sell_in = models.FloatField(default=0) # iniziali
    published_date = models.DateTimeField(blank=True, null=True)
    ended = models.BooleanField(default=False) # trans conclusa
    good = models.BooleanField(default=False)  # trans buona ma non conclusa
    winner = models.TextField(max_length=50, default='')
    price_1B_end = models.FloatField(default=0)   # prezzo 1B venduto
    total_B_exchanged = models.FloatField(default=0)   # quantità di B venduta
    total_price = models.FloatField(default=0)   # prezzo totale scambiato per la transazione

    def publish(self):
        self.published_date = timezone.now()
        self.save()