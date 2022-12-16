# Generated by Django 3.2.16 on 2022-12-16 18:21

from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('duo', '0002_auto_20221216_1013'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataUseModifier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.CharField(help_text='The identifier of this consent group (e.g., DUO:0000045).', max_length=31, unique=True)),
                ('abbreviation', models.CharField(help_text='The short code for this consent group (e.g., GRU).', max_length=15)),
                ('term', models.CharField(help_text='The term associated this instance (e.g., general research use).', max_length=255)),
                ('definition', models.TextField(help_text='The definition for this term.')),
                ('comment', models.TextField(blank=True, help_text='Comments associated with this term.')),
                ('lft', models.PositiveIntegerField(editable=False)),
                ('rght', models.PositiveIntegerField(editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(editable=False)),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='duo.datausemodifier')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
