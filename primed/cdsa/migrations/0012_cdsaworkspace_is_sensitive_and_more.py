# Generated by Django 4.2.8 on 2024-01-30 00:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cdsa", "0011_signedagreement_add_replaced_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="cdsaworkspace",
            name="is_sensitive",
            field=models.BooleanField(
                default=False,
                help_text="Indicator of whether this workspace contains sensitive data.",
                verbose_name="Sensitive?",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="historicalcdsaworkspace",
            name="is_sensitive",
            field=models.BooleanField(
                default=False,
                help_text="Indicator of whether this workspace contains sensitive data.",
                verbose_name="Sensitive?",
            ),
            preserve_default=False,
        ),
    ]
