# Generated by Django 3.2.19 on 2023-09-13 23:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cdsa', '0007_alter_agreementversion_major_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='agreementmajorversion',
            name='is_valid',
            field=models.BooleanField(default=True, help_text='Boolean indicator of whether this version is valid.', verbose_name='Valid?'),
        ),
        migrations.AddField(
            model_name='historicalagreementmajorversion',
            name='is_valid',
            field=models.BooleanField(default=True, help_text='Boolean indicator of whether this version is valid.', verbose_name='Valid?'),
        ),
    ]
