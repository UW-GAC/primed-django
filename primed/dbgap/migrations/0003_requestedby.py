# Generated by Django 3.2.16 on 2022-12-09 00:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dbgap', '0002_dbgapdataacessrequest_dbgap_dac'),
    ]

    operations = [
        migrations.AddField(
            model_name='dbgapworkspace',
            name='requested_by',
            field=models.ForeignKey(default=None, help_text='The user who requested creation.', on_delete=django.db.models.deletion.PROTECT, to='users.user'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicaldbgapworkspace',
            name='requested_by',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='The user who requested creation.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
    ]
