# Generated by Django 4.2.10 on 2024-03-12 21:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cdsa", "0014_gsr_restricted_help_and_verbose"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataaffiliateagreement",
            name="additional_limitations",
            field=models.TextField(
                blank=True,
                help_text="Additional limitations on data use as specified in the signed CDSA.",
            ),
        ),
        migrations.AddField(
            model_name="historicaldataaffiliateagreement",
            name="additional_limitations",
            field=models.TextField(
                blank=True,
                help_text="Additional limitations on data use as specified in the signed CDSA.",
            ),
        ),
    ]
