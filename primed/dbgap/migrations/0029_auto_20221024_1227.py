# Generated by Django 3.2.13 on 2022-10-24 19:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbgap', '0028_historicaldbgapdataaccesssnapshot'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dbgapstudyaccession',
            old_name='phs',
            new_name='dbgap_phs',
        ),
        migrations.RenameField(
            model_name='historicaldbgapstudyaccession',
            old_name='phs',
            new_name='dbgap_phs',
        ),
    ]
