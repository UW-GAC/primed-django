import re

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from tree_queries.models import TreeNode, TreeNodeForeignKey


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

    def get_short_definition(self):
        text = re.sub(r"This .+? indicates that ", "", self.definition)
        # Only capitalize the first letter - keep the remaining text as is.
        text = text[0].capitalize() + text[1:]
        return text


class DataUsePermission(DUOFields, TreeNode):
    """A model to track the allowed main consent codes using GA4GH DUO codes."""

    requires_disease_term = models.BooleanField(
        default=False,
        help_text="Indicator of whether an additional disease term is required for this term.",
    )

    def get_absolute_url(self):
        return reverse("duo:data_use_permissions:detail", args=[self.identifier])


class DataUseModifier(DUOFields, TreeNode):
    """A model to track the allowed consent modifiers using GA4GH DUO codes."""

    def get_absolute_url(self):
        return reverse("duo:data_use_modifiers:detail", args=[self.identifier])


class DataUseOntologyModel(models.Model):
    """An abstract model to track a group using Data Use Ontology terms to describe allowed data use."""

    data_use_permission = TreeNodeForeignKey(
        DataUsePermission,
        verbose_name="DUO data use permission",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text="""The DataUsePermission associated with this study-consent group.""",
    )
    data_use_modifiers = models.ManyToManyField(
        DataUseModifier,
        verbose_name="DUO data use modifiers",
        blank=True,
        help_text="""The DataUseModifiers associated with this study-consent group.""",
    )
    disease_term = models.CharField(
        verbose_name="DUO disease term",
        max_length=255,
        blank=True,
        null=True,
        help_text="The disease term if required by data_use_permission.",
    )

    class Meta:
        abstract = True

    def clean(self):
        """Ensure that disease_term is set if data_use_permission requires it."""
        # Without hasattr, we get a RelatedObjectDoesNotExist error.
        if hasattr(self, "data_use_permission") and self.data_use_permission:
            if self.data_use_permission.requires_disease_term and not self.disease_term:
                raise ValidationError(
                    "`disease_term` must not be None "
                    "because data_use_permission requires a disease restriction."
                )
            if not self.data_use_permission.requires_disease_term and self.disease_term:
                raise ValidationError(
                    (
                        "`disease_term` must be None "
                        "because data_use_permission does not require a disease restriction."
                    )
                )
