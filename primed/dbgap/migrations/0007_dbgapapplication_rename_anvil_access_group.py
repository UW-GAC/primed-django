# Generated by Django 3.2.16 on 2023-03-29 16:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbgap', '0006_dbgapworkspace_available_data'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dbgapapplication',
            old_name='anvil_group',
            new_name='anvil_access_group',
        ),
        migrations.RenameField(
            model_name='historicaldbgapapplication',
            old_name='anvil_group',
            new_name='anvil_access_group',
        ),
    ]
