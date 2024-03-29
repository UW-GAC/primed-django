# Generated by Django 3.2.16 on 2022-12-02 22:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbgap', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dbgapdataaccessrequest',
            name='dbgap_dac',
            field=models.CharField(default='', help_text='The Data Access Committee for this DAR.', max_length=31, verbose_name=' dbGaP DAC'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicaldbgapdataaccessrequest',
            name='dbgap_dac',
            field=models.CharField(default='', help_text='The Data Access Committee for this DAR.', max_length=31, verbose_name=' dbGaP DAC'),
            preserve_default=False,
        ),
    ]
