# Generated by Django 4.2.10 on 2024-03-18 17:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cdsa", "0021_populate_is_primary"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="historicalsignedagreement",
            name="is_primary",
        ),
        migrations.RemoveField(
            model_name="signedagreement",
            name="is_primary",
        ),
    ]
