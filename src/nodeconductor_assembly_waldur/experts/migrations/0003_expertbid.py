# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-11 07:41
from __future__ import unicode_literals

from decimal import Decimal
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import nodeconductor.core.fields
import nodeconductor.structure.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('structure', '0052_customer_subnets'),
        ('experts', '0002_expertrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpertBid',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('uuid', nodeconductor.core.fields.UUIDField()),
                ('price', models.DecimalField(decimal_places=7, default=0, max_digits=22, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='experts.ExpertRequest')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='structure.Project')),
                ('user', models.ForeignKey(help_text='The user which has created this bid.', on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created'],
            },
            bases=(nodeconductor.structure.models.StructureLoggableMixin, models.Model),
        ),
    ]