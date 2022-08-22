from django.db import models


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


class StudyConsentGroup(models.Model):
    """A model to track study-consent groups."""

    study = models.ForeignKey(Study, on_delete=models.PROTECT)
    """The Study associated with this study-consent group."""

    data_use_permission = models.ForeignKey(DataUsePermission, on_delete=models.PROTECT)
    """The DataUsePermission associated with this study-consent group."""

    data_use_modifiers = models.ManyToManyField(DataUseModifier)
    """The DataUseModifiers associated with this study consent group."""

    full_consent_code = models.CharField(max_length=63)
    """The full consent code for this study consent group (e.g., GRU-NPU-MDS).

    This field would ideally be created from main_consent + consent_modifiers to minimize data duplication.
    Unfortunately, there are often legacy codes that don't fit into the current main/modifiers model.
    We also need this field to match to dbGaP authorized access, so store it separately."""

    data_use_limitations = models.TextField()
    """The full data use limitations for this study consent group."""

    class Meta:
        constraints = [
            # Model uniqueness.
            models.UniqueConstraint(
                name="unique_study_consent_group",
                fields=["study", "full_consent_code"],
            ),
        ]

    def __str__(self):
        """String method.
        Returns:
            A string showing the study and full consent code of the object.
        """
        return "{} - {}".format(self.study, self.full_consent_code)
