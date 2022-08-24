from anvil_consortium_manager.models import BaseWorkspaceData
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class StudySite(models.Model):
    """A model to track Study Sites."""

    short_name = models.CharField(max_length=31, unique=True)
    """The short name for this Study."""

    full_name = models.CharField(max_length=255)
    """The full name for this Study."""

    def __str__(self):
        """String method.
        Returns:
            A string showing the short name of the object.
        """
        return self.short_name


class Study(models.Model):
    """A model to track studies."""

    short_name = models.CharField(max_length=31, unique=True)
    """The short name for this Study."""

    full_name = models.CharField(max_length=255)
    """The full name for this Study."""

    def __str__(self):
        """String method.
        Returns:
            A string showing the short name of the object.
        """
        return self.short_name

    def get_absolute_url(self):
        """Return the absolute url for this object."""
        return reverse("primed_anvil:studies:detail", args=[self.pk])


class DataUsePermission(models.Model):
    """A model to track the allowed main consent codes using GA4GH DUO codes."""

    # Consider separating this into a main consent code and a set of modifiers.
    code = models.CharField(max_length=15, unique=True)
    """The short consent code (e.g., GRU)."""

    description = models.CharField(max_length=255, unique=True)
    """The description for this consent code (e.g., General Research Use)."""

    identifier = models.CharField(max_length=31, unique=True)
    """The identifier of this modifier (e.g., DUO:0000045)."""

    def __str__(self):
        """String method.
        Returns:
            A string showing the short consent code of the object.
        """
        return self.code


class DataUseModifier(models.Model):
    """A model to track the allowed consent modifiers using GA4GH DUO codes."""

    code = models.CharField(max_length=15, unique=True)
    """The short consent code (e.g., NPU)."""

    description = models.CharField(max_length=255, unique=True)
    """The description of the consent code (e.g., Non-Profit Use only)."""

    identifier = models.CharField(max_length=31, unique=True)
    """The identifier of this modifier (e.g., DUO:0000045)."""

    def __str__(self):
        """String method.
        Returns:
            A string showing the short consent code of the object.
        """
        return self.code


class DataUseOntologyModel(models.Model):
    """An abstract model to track a group using Data Use Ontology terms to describe allowed data use."""

    data_use_permission = models.ForeignKey(DataUsePermission, on_delete=models.PROTECT)
    """The DataUsePermission associated with this study-consent group."""

    data_use_modifiers = models.ManyToManyField(DataUseModifier, blank=True)
    """The DataUseModifiers associated with this study consent group."""

    class Meta:
        abstract = True


class dbGaPWorkspace(DataUseOntologyModel, BaseWorkspaceData):
    """A model to track additional data about dbGaP data in a workspace."""

    study = models.ForeignKey(Study, on_delete=models.PROTECT)
    """The Study associated with this Workspace."""

    # Should this be here or in the abstract DataUseOntology model?
    full_consent_code = models.CharField(max_length=63)
    """The full consent code for this study consent group (e.g., GRU-NPU-MDS).

    This field would ideally be created from main_consent + consent_modifiers to minimize data duplication.
    Unfortunately, there are often legacy codes that don't fit into the current main/modifiers model.
    We also need this field to match to dbGaP authorized access, so store it separately."""

    data_use_limitations = models.TextField()
    """The full data use limitations for this workspace."""

    # Should some of these be their own model?
    # PositiveIntegerField allows 0 and we want this to be 1 or higher.
    # We'll need to add a separate constraint.
    phs = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    """The dbGaP study accession associated with this workspace (e.g., phs000007)."""

    # Do we want version here?
    version = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    """The dbGaP version associated with this Workspace."""

    # Do we want version here?
    participant_set = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    """The dbGaP participant set associated with this Workspace."""

    class Meta:
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
