from anvil_consortium_manager.models import BaseWorkspaceData
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel

from ..primed_anvil.models import DataUseOntologyModel, Study


class dbGaPStudyAccession(TimeStampedModel, models.Model):
    """A model to track dbGaP study accessions."""

    # Consider making this many to many since some dbgap acessions contain multiple studies.
    study = models.ForeignKey(
        Study,
        on_delete=models.PROTECT,
        help_text="The study associated with this dbGaP study accession.",
    )
    phs = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        unique=True,
        help_text="""The dbGaP study accession integer associated with this workspace (e.g., 7 for phs000007).""",
    )

    class Meta:
        # Add a white space to prevent autocapitalization fo the "d" in "dbGaP".
        verbose_name = " dbGaP study accession"
        verbose_name_plural = " dbGaP study accessions"

    def __str__(self):
        return "phs{phs:06d} - {study}".format(
            phs=self.phs, study=self.study.short_name
        )

    def get_absolute_url(self):
        return reverse("dbgap:dbgap_study_accessions:detail", kwargs={"pk": self.pk})


class dbGaPWorkspace(DataUseOntologyModel, TimeStampedModel, BaseWorkspaceData):
    """A model to track additional data about dbGaP data in a workspace."""

    # PositiveIntegerField allows 0 and we want this to be 1 or higher.
    # We'll need to add a separate constraint.
    dbgap_study_accession = models.ForeignKey(
        dbGaPStudyAccession, on_delete=models.PROTECT
    )

    # Should dbgap_study, version and participant set be their own model -- dbGaPStudyVersion?
    # Note that having this -- wec ould have derived data workspaces linking to multiple dbgap study versions.
    dbgap_version = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="""The dbGaP study version associated with this Workspace.""",
    )

    # Do we want version here?
    dbgap_participant_set = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="""The dbGaP participant set associated with this Workspace.""",
    )

    # Should this be here or in the abstract DataUseOntology model?
    full_consent_code = models.CharField(
        max_length=63,
        help_text="""The full consent code from dbGaP for this study consent group (e.g., GRU-NPU-MDS).""",
    )
    # This field would ideally be created from the DataUseOntology fields to minimize data duplication.
    # Unfortunately, there are often legacy codes that don't fit into the current main/modifiers model.
    # We also need this field to match to dbGaP authorized access, so store it separately."""

    data_use_limitations = models.TextField(
        help_text="""The full data use limitations for this workspace."""
    )

    class Meta:
        # Add a white space to prevent autocapitalization fo the "d" in "dbGaP".
        verbose_name = " dbGaP workspace"
        verbose_name_plural = " dbGaP workspaces"
        constraints = [
            # Model uniqueness.
            models.UniqueConstraint(
                name="unique_dbgap_workspace",
                fields=["dbgap_study_accession", "dbgap_version", "full_consent_code"],
            ),
        ]

    def __str__(self):
        """String method.
        Returns:
            A string showing the workspace name of the object.
        """
        return "{} ({} - {})".format(
            self.dbgap_study_accession.study.short_name,
            self.get_dbgap_accession(),
            self.full_consent_code,
        )

    def get_dbgap_accession(self):
        return "phs{phs:06d}.v{v}.p{ps}".format(
            phs=self.dbgap_study_accession.phs,
            v=self.dbgap_version,
            ps=self.dbgap_participant_set,
        )
