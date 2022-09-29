# Generated by Django 3.2.13 on 2022-09-29 20:20

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbgap', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dbgapstudy',
            name='phs',
            field=models.PositiveIntegerField(help_text='The dbGaP study accession associated with this workspace (e.g., phs000007).', unique=True, validators=[django.core.validators.MinValueValidator(1)]),
        ),
    ]
