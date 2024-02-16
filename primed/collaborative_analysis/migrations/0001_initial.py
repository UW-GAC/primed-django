# Generated by Django 4.2.7 on 2023-12-07 00:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import simple_history.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("anvil_consortium_manager", "0015_add_new_permissions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalCollaborativeAnalysisWorkspace",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name="modified"
                    ),
                ),
                (
                    "purpose",
                    models.TextField(
                        help_text="The intended purpose for this workspace."
                    ),
                ),
                (
                    "proposal_id",
                    models.IntegerField(
                        blank=True,
                        help_text="The ID of the proposal that this workspace is associated with.",
                        null=True,
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "analyst_group",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="The AnVIL group containing analysts for this workspace.",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="anvil_consortium_manager.managedgroup",
                    ),
                ),
                (
                    "custodian",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="The custodian for this workspace.",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="anvil_consortium_manager.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical collaborative analysis workspace",
                "verbose_name_plural": "historical collaborative analysis workspaces",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="CollaborativeAnalysisWorkspace",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name="modified"
                    ),
                ),
                (
                    "purpose",
                    models.TextField(
                        help_text="The intended purpose for this workspace."
                    ),
                ),
                (
                    "proposal_id",
                    models.IntegerField(
                        blank=True,
                        help_text="The ID of the proposal that this workspace is associated with.",
                        null=True,
                    ),
                ),
                (
                    "analyst_group",
                    models.ForeignKey(
                        help_text="The AnVIL group containing analysts for this workspace.",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="anvil_consortium_manager.managedgroup",
                    ),
                ),
                (
                    "custodian",
                    models.ForeignKey(
                        help_text="The custodian for this workspace.",
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_workspaces",
                    models.ManyToManyField(
                        help_text="Workspaces contributing data to this workspace.",
                        related_name="collaborative_analysis_workspaces",
                        to="anvil_consortium_manager.workspace",
                    ),
                ),
                (
                    "workspace",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="anvil_consortium_manager.workspace",
                    ),
                ),
            ],
            options={
                "get_latest_by": "modified",
                "abstract": False,
            },
        ),
    ]
