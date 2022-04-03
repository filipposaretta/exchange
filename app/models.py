from django.contrib.auth.models import User
from djongo.models.fields import ObjectIdField
from django.utils import timezone
from djongo import models

class Wallet(models.Model):
    _id = ObjectIdField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    username = models.TextField(max_length=50, default='')
    datetime = models.DateTimeField(auto_now_add=True)
    bitcoin = models.FloatField()
    dollars = models.FloatField()
    bitcoin_init = models.FloatField()
    dollars_init = models.FloatField()

class Trans(models.Model):
    _id = ObjectIdField()
    one_B_dollar = models.FloatField(default=0)  #initial $/B
    creator = models.TextField(max_length=50, default='')
    buy = models.FloatField(default=0)  #bitcoin
    sell = models.FloatField(default=0)  #bitcoin
    buy_in = models.FloatField(default=0) #initial
    sell_in = models.FloatField(default=0) #initial
    published_date = models.DateTimeField(blank=True, null=True)
    ended = models.BooleanField(default=False) #trans approved
    good = models.BooleanField(default=False)  #trans good, it can be approved
    winner = models.TextField(max_length=50, default='')
    price_1B_sell = models.FloatField(default=0)
    quantity_B_sell = models.FloatField(default=0)
    total_dollars_sell = models.FloatField(default=0)

    def publish(self):
        self.published_date = timezone.now()
        self.save()

# Create your models here.
