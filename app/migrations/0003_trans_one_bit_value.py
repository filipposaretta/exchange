# Generated by Django 2.1.5 on 2022-02-13 17:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_remove_trans_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='trans',
            name='one_bit_value',
            field=models.FloatField(default=0),
        ),
    ]