# Generated by Django 3.2.13 on 2022-10-19 00:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dbgap', '0020_auto_20221018_1615'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dbgapdataaccesssnapshot',
            options={'verbose_name': ' dbGaP data access snapshot'},
        ),
        migrations.CreateModel(
            name='HistoricaldbGaPDataAccessSnapshot',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('dbgap_dar_data', models.JSONField(null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('dbgap_application', models.ForeignKey(blank=True, db_constraint=False, help_text='The dbGaP application associated with this DAR.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='dbgap.dbgapapplication', verbose_name='dbGaP application')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical  dbGaP data access snapshot',
                'verbose_name_plural': 'historical  dbGaP data access snapshots',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
