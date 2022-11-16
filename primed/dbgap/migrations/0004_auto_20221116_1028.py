# Generated by Django 3.2.13 on 2022-11-16 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbgap', '0003_auto_20221115_1342'),
    ]

    operations = [
        migrations.AddField(
            model_name='dbgapdataaccesssnapshot',
            name='is_most_recent',
            field=models.BooleanField(default=False, help_text='Indicator of whether this is the most recent snapshot for this applicaiton.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicaldbgapdataaccesssnapshot',
            name='is_most_recent',
            field=models.BooleanField(default=False, help_text='Indicator of whether this is the most recent snapshot for this applicaiton.'),
            preserve_default=False,
        ),
    ]
