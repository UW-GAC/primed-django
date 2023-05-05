# Generated by Django 3.2.16 on 2023-03-29 16:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('anvil_consortium_manager', '0008_workspace_is_locked'),
        ('dbgap', '0007_dbgapapplication_rename_anvil_access_group'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dbgapapplication',
            name='anvil_access_group',
            field=models.OneToOneField(help_text='The AnVIL managed group that can will access to workspaces under this dbGaP application.', on_delete=django.db.models.deletion.PROTECT, to='anvil_consortium_manager.managedgroup', verbose_name=' AnVIL access group'),
        ),
        migrations.AlterField(
            model_name='historicaldbgapapplication',
            name='anvil_access_group',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='The AnVIL managed group that can will access to workspaces under this dbGaP application.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='anvil_consortium_manager.managedgroup', verbose_name=' AnVIL access group'),
        ),
    ]