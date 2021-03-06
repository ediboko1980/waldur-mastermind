# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-07-03 17:02
from django.db import migrations

import waldur_core.core.fields


class Migration(migrations.Migration):

    dependencies = [
        ('structure', '0001_squashed_0054'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicesettings',
            name='geolocations',
            field=waldur_core.core.fields.JSONField(
                blank=True,
                default=list,
                help_text='List of latitudes and longitudes. For example: [{"latitude": 123, "longitude": 345}, {"latitude": 456, "longitude": 678}]',
            ),
        ),
        migrations.AlterField(
            model_name='servicesettings',
            name='options',
            field=waldur_core.core.fields.JSONField(
                blank=True, default=dict, help_text='Extra options'
            ),
        ),
    ]
