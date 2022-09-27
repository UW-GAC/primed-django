from anvil_consortium_manager.models import BaseWorkspaceData
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel


class Study(TimeStampedModel, models.Model):
    """A model to track studies."""

    short_name = models.CharField(
        max_length=31, unique=True, help_text="The short name for this Study."
    )
    full_name = models.CharField(
        max_length=255, help_text="The full name for this Study."
    )

    class Meta:
        verbose_name_plural = "studies"

    def __str__(self):
        """String method.
        Returns:
            A string showing the short name of the object.
        """
        return self.short_name

    def get_absolute_url(self):
        """Return the absolute url for this object."""
        return reverse("primed_anvil:studies:detail", args=[self.pk])


class DataUsePermission(TimeStampedModel, models.Model):
    """A model to track the allowed main consent codes using GA4GH DUO codes."""

    # Consider separating this into a main consent code and a set of modifiers.
    code = models.CharField(
        max_length=15, unique=True, help_text="""The short consent code (e.g., GRU)."""
    )
    description = models.CharField(
        max_length=255,
        unique=True,
        help_text="""The description for this consent code (e.g., General Research Use).""",
    )
    identifier = models.CharField(
        max_length=31,
        unique=True,
        help_text="""The identifier of this modifier (e.g., DUO:0000045).""",
    )
    requires_disease_restriction = models.BooleanField(
        default=False,
        help_text="Indicator of whether an additional disease restriction is required for this term.",
    )

    def __str__(self):
        """String method.
        Returns:
            A string showing the short consent code of the object.
        """
        return self.code


class DataUseModifier(TimeStampedModel, models.Model):
    """A model to track the allowed consent modifiers using GA4GH DUO codes."""

    code = models.CharField(
        max_length=15, unique=True, help_text="""The short consent code (e.g., NPU)."""
    )
    description = models.CharField(
        max_length=255,
        unique=True,
        help_text="""The description of the consent code (e.g., Non-Profit Use only).""",
    )
    identifier = models.CharField(
        max_length=31,
        unique=True,
        help_text="""The identifier of this modifier (e.g., DUO:0000045).""",
    )

    def __str__(self):
        """String method.
        Returns:
            A string showing the short consent code of the object.
        """
        return self.code


class DataUseOntologyModel(models.Model):
    """An abstract model to track a group using Data Use Ontology terms to describe allowed data use."""

    data_use_permission = models.ForeignKey(
        DataUsePermission,
        on_delete=models.PROTECT,
        help_text="""The DataUsePermission associated with this study-consent group.""",
    )
    data_use_modifiers = models.ManyToManyField(
        DataUseModifier,
        blank=True,
        help_text="""The DataUseModifiers associated with this study consent group.""",
    )
    disease_restriction = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The disease restriction if required by data_use_permission.",
    )

    class Meta:
        abstract = True

    def clean(self):
        """Ensure that the disease_restriction term is set if data_use_permission requires it."""
        # Without hasattr, we get a RelatedObjectDoesNotExist error.
        if hasattr(self, "data_use_permission"):
            if (
                self.data_use_permission.requires_disease_restriction
                and not self.disease_restriction
            ):
                raise ValidationError(
                    "`disease_restriction` must not be None "
                    "because data_use_permission requires a disease restriction."
                )
            if (
                not self.data_use_permission.requires_disease_restriction
                and self.disease_restriction
            ):
                raise ValidationError(
                    (
                        "`disease_restriction` must be None "
                        "because data_use_permission does not require a disease restriction."
                    )
                )


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
