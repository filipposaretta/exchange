# Generated by Django 2.1.5 on 2022-03-02 20:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_trans_bc'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='trans',
            name='bc',
        ),
    ]