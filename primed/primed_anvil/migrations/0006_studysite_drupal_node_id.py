# Generated by Django 3.2.19 on 2023-12-06 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('primed_anvil', '0005_availabledata'),
    ]

    operations = [
        migrations.AddField(
            model_name='studysite',
            name='drupal_node_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]