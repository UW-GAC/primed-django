from anvil_consortium_manager.models import BaseWorkspaceData
from django.core.validators import MinValueValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from ..primed_anvil.models import DataUseOntologyModel, Study


class dbGaPWorkspace(DataUseOntologyModel, TimeStampedModel, BaseWorkspaceData):
    """A model to track additional data about dbGaP data in a workspace."""

    study = models.ForeignKey(
        Study,
        on_delete=models.PROTECT,
        help_text="""The Study associated with this Workspace.""",
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

    # Should some of these be their own model?
    # PositiveIntegerField allows 0 and we want this to be 1 or higher.
    # We'll need to add a separate constraint.
    phs = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="""The dbGaP study accession associated with this workspace (e.g., phs000007).""",
    )

    # Do we want version here?
    version = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="""The dbGaP study version associated with this Workspace.""",
    )

    # Do we want version here?
    participant_set = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="""The dbGaP participant set associated with this Workspace.""",
    )

    class Meta:
        # Add a white space to prevent autocapitalization fo the "d" in "dbGaP".
        verbose_name = " dbGaP workspace"
        verbose_name_plural = " dbGaP workspaces"
        constraints = [
            # Model uniqueness.
            models.UniqueConstraint(
                name="unique_dbgap_workspace",
                fields=["study", "phs", "version"],
            ),
        ]

    def __str__(self):
        """String method.
        Returns:
            A string showing the workspace name of the object.
        """
        return "{} - {}".format(self.get_dbgap_accession(), self.full_consent_code)

    def get_dbgap_accession(self):
        return "phs{phs:06d}.v{v}.p{ps}".format(
            phs=self.phs,
            v=self.version,
            ps=self.participant_set,
        )
