# Generated by Django 3.2.19 on 2023-08-31 22:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cdsa', '0004_populate_agreementmajorversion'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='agreementversion',
            options={'get_latest_by': 'modified'},
        ),
        migrations.RemoveConstraint(
            model_name='agreementversion',
            name='unique_agreement_version',
        ),
        migrations.RemoveField(
            model_name='agreementversion',
            name='major_version',
        ),
        migrations.RemoveField(
            model_name='historicalagreementversion',
            name='major_version',
        ),
    ]