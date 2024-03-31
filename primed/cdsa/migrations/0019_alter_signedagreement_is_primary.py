# Generated by Django 4.2.10 on 2024-03-18 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cdsa", "0018_dataaffiliateagreement_requires_study_review_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalsignedagreement",
            name="is_primary",
            field=models.BooleanField(
                help_text="Indicator of whether this is a primary Agreement (and not a component Agreement).",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="signedagreement",
            name="is_primary",
            field=models.BooleanField(
                help_text="Indicator of whether this is a primary Agreement (and not a component Agreement).",
                null=True,
            ),
        ),
    ]