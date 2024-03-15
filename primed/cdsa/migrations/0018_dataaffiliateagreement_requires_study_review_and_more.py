# Generated by Django 4.2.10 on 2024-03-15 20:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cdsa", "0017_alter_cdsaworkspace_additional_limitations_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataaffiliateagreement",
            name="requires_study_review",
            field=models.BooleanField(
                default=False,
                help_text="Indicator of whether indicates investigators need to have an approved PRIMED paper proposal where this dataset was selected and approved in order to work with data brought under this CDSA.",
            ),
        ),
        migrations.AddField(
            model_name="historicaldataaffiliateagreement",
            name="requires_study_review",
            field=models.BooleanField(
                default=False,
                help_text="Indicator of whether indicates investigators need to have an approved PRIMED paper proposal where this dataset was selected and approved in order to work with data brought under this CDSA.",
            ),
        ),
    ]
