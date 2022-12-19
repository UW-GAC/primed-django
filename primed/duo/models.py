from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField


class DUOFields(models.Model):
    """Field definitions for DUO models."""

    identifier = models.CharField(
        max_length=31,
        unique=True,
        help_text="""The identifier of this consent group (e.g., DUO:0000045).""",
    )
    abbreviation = models.CharField(
        max_length=15,
        help_text="""The short code for this consent group (e.g., GRU).""",
    )
    term = models.CharField(
        max_length=255,
        help_text="""The term associated this instance (e.g., general research use).""",
    )
    definition = models.TextField(help_text="The definition for this term.")
    comment = models.TextField(
        help_text="Comments associated with this term.",
        blank=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        """String method.
        Returns:
            A string showing the short consent code of the object.
        """
        return "{}".format(self.term)

    def get_ols_url(self):
        return "http://purl.obolibrary.org/obo/{}".format(
            self.identifier.replace("DUO:", "DUO_")
        )


class DataUsePermission(DUOFields, MPTTModel):
    """A model to track the allowed main consent codes using GA4GH DUO codes."""

    requires_disease_restriction = models.BooleanField(
        default=False,
        help_text="Indicator of whether an additional disease restriction is required for this term.",
    )

    # Required for MPTT.
    parent = TreeForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    class MPTTMeta:
        order_insertion_by = ["identifier"]

    def get_absolute_url(self):
        return reverse("duo:data_use_permissions:detail", args=[self.identifier])


class DataUseModifier(DUOFields, MPTTModel):
    """A model to track the allowed consent modifiers using GA4GH DUO codes."""

    # Required for MPTT.
    parent = TreeForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    class MPTTMeta:
        order_insertion_by = ["identifier"]

    def get_absolute_url(self):
        return reverse("duo:data_use_modifiers:detail", args=[self.identifier])


class DataUseOntologyModel(models.Model):
    """An abstract model to track a group using Data Use Ontology terms to describe allowed data use."""

    data_use_permission = TreeForeignKey(
        DataUsePermission,
        verbose_name="DUO data use permission",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text="""The DataUsePermission associated with this study-consent group.""",
    )
    data_use_modifiers = TreeManyToManyField(
        DataUseModifier,
        verbose_name="DUO data use modifiers",
        blank=True,
        help_text="""The DataUseModifiers associated with this study-consent group.""",
    )
    # TODO: Change to disease_term instead of disease_restriction.
    disease_restriction = models.CharField(
        verbose_name="DUO disease restriction",
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
        if hasattr(self, "data_use_permission") and self.data_use_permission:
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
