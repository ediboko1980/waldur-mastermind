# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-18 16:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0012_add_product_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='packagetemplate',
            name='article_code',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]