# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-03-12 11:17
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0060_plan_backend_id'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ProjectResourceCount',
            new_name='AggregateResourceCount',
        ),
    ]