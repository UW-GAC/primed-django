# Generated by Django 4.2.8 on 2024-01-30 00:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dbgap", "0008_dbgapapplication_anvil_access_group_verbose"),
    ]

    operations = [
        migrations.AddField(
            model_name="dbgapworkspace",
            name="is_sensitive",
            field=models.BooleanField(
                default=False,
                help_text="Indicator of whether this workspace contains sensitive data.",
                verbose_name="Sensitive?",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="historicaldbgapworkspace",
            name="is_sensitive",
            field=models.BooleanField(
                default=False,
                help_text="Indicator of whether this workspace contains sensitive data.",
                verbose_name="Sensitive?",
            ),
            preserve_default=False,
        ),
    ]
