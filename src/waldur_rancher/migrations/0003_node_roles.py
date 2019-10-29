# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2019-10-15 13:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('waldur_rancher', '0002_cluster_backend_id_not_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='controlplane_role',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='node',
            name='etcd_role',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='node',
            name='worker_role',
            field=models.BooleanField(default=False),
        ),
    ]