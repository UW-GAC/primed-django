# Generated by Django 3.2.19 on 2023-08-31 18:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cdsa', '0002_agreementmajorversion_historicalagreementmajorversion'),
    ]

    operations = [
        migrations.AddField(
            model_name='agreementversion',
            name='major_version_fk',
            field=models.ForeignKey(blank=True, help_text='Major version of the CDSA. Changes to the major version require resigning.', null=True, on_delete=django.db.models.deletion.CASCADE, to='cdsa.agreementmajorversion'),
        ),
        migrations.AddField(
            model_name='historicalagreementversion',
            name='major_version_fk',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='Major version of the CDSA. Changes to the major version require resigning.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='cdsa.agreementmajorversion'),
        ),
    ]
