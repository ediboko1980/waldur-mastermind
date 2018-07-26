# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-07 10:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('waldur_jira', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='resource_content_type',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='jira_issues', to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='issue',
            name='resource_object_id',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
    ]