# Generated by Django 3.2.16 on 2023-01-10 19:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('primed_anvil', '0005_availabledata'),
        ('anvil_consortium_manager', '0005_help_text'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('miscellaneous_workspaces', '0005_requestedby'),
    ]

    operations = [
        migrations.CreateModel(
            name='OpenAccessWorkspace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('data_source', models.TextField()),
                ('available_data', models.ManyToManyField(blank=True, help_text='The types of data available in this workspace.', to='primed_anvil.AvailableData')),
                ('requested_by', models.ForeignKey(help_text='The user who requested creation.', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('studies', models.ManyToManyField(help_text='The studies associated with this workspace.', to='primed_anvil.Study')),
                ('workspace', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='anvil_consortium_manager.workspace')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='HistoricalOpenAccessWorkspace',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('data_source', models.TextField()),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('requested_by', models.ForeignKey(blank=True, db_constraint=False, help_text='The user who requested creation.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='anvil_consortium_manager.workspace')),
            ],
            options={
                'verbose_name': 'historical open access workspace',
                'verbose_name_plural': 'historical open access workspaces',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
