"""Model defintions for the `cdsa` app."""

from datetime import date

from anvil_consortium_manager.models import (
    BaseWorkspaceData,
    GroupGroupMembership,
    ManagedGroup,
)
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel
from model_utils.models import StatusModel
from simple_history.models import HistoricalRecords

from primed.duo.models import DataUseOntologyModel
from primed.primed_anvil.models import AvailableData, RequesterModel, Study, StudySite


class AgreementMajorVersion(TimeStampedModel, models.Model):
    """A model for a major agreement version."""

    version = models.IntegerField(
        help_text="Major version of the CDSA. Changes to the major version require resigning.",
        validators=[MinValueValidator(1)],
        unique=True,
    )
    is_valid = models.BooleanField(
        default=True, help_text="Boolean indicator of whether this version is valid."
    )

    history = HistoricalRecords()

    def __str__(self):
        return "v{}".format(self.version)

    def get_absolute_url(self):
        return reverse(
            "cdsa:agreement_versions:major_version_detail",
            kwargs={
                "major_version": self.version,
            },
        )


class AgreementVersion(TimeStampedModel, models.Model):
    """Model to track approved CDSA versions."""

    major_version = models.ForeignKey(
        AgreementMajorVersion,
        help_text="Major version of the CDSA. Changes to the major version require resigning.",
        on_delete=models.CASCADE,
    )
    minor_version = models.IntegerField(
        help_text="Minor version of the CDSA. Changes to the minor version do not require resigning.",
        validators=[MinValueValidator(0)],
    )
    date_approved = models.DateField(
        help_text="Date that this AgreementVersion was approved by the PRIMED Consortium.",
        default=date.today,
    )

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["major_version", "minor_version"],
                name="unique_agreement_version_2",
            )
        ]
        ordering = ["major_version", "minor_version"]

    def __str__(self):
        return self.full_version

    def get_absolute_url(self):
        return reverse(
            "cdsa:agreement_versions:detail",
            kwargs={
                "major_version": self.major_version.version,
                "minor_version": self.minor_version,
            },
        )

    @property
    def full_version(self):
        return "{}.{}".format(str(self.major_version), self.minor_version)


class SignedAgreementStatusMixin:
    """Mixin to define status choices for SignedAgreements."""

    # This is required because we are using django-model-util's StatusModel with django-simple-history:
    # See GitHub issue: https://github.com/jazzband/django-simple-history/issues/190

    class StatusChoices(models.TextChoices):
        ACTIVE = "active", "Active"
        """SignedAgreements that are currently active."""  # pragma: no cover

        WITHDRAWN = "withdrawn", "Withdrawn"
        """SignedAgreements that have been withdrawn for some reason (e.g., PI changed institution,
        study no longer wanted to participate.)"""

        LAPSED = "lapsed", "Lapsed"
        """SignedAgreements from a AgreementMajorVersion that is no longer valid."""  # pragma: no cover

        REPLACED = "replaced", "Replaced"
        """SignedAgreements that have been replaced by a newer version."""  # pragma: no cover

    STATUS = StatusChoices.choices


class SignedAgreement(
    TimeStampedModel, SignedAgreementStatusMixin, StatusModel, models.Model
):
    """Model to track verified, signed consortium data sharing agreements."""

    MEMBER = "member"
    DATA_AFFILIATE = "data_affiliate"
    NON_DATA_AFFILIATE = "non_data_affiliate"
    TYPE_CHOICES = (
        (MEMBER, "Member"),
        (DATA_AFFILIATE, "Data affiliate"),
        (NON_DATA_AFFILIATE, "Non-data affiliate"),
    )

    cc_id = models.IntegerField(
        help_text="Identifier assigned by the Coordinating Center.",
        unique=True,
        validators=[MinValueValidator(1)],
    )
    representative = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        help_text="The investigator who signed this Agreement.",
    )
    representative_role = models.CharField(
        max_length=255,
        help_text="Representative's role in the group.",
    )
    # We don't have an institution model so this has to be free text.
    # We also don't want to link to the representative's institution, since this should *not* update
    # if the investigator changes institutions.
    signing_institution = models.CharField(
        max_length=255,
        help_text="Signing institution for this Agreement.",
    )
    # This is needed to know which agreement type model to link to, and to validate the agreement type model itself.
    type = models.CharField(
        verbose_name="Agreement type",
        max_length=31,
        choices=TYPE_CHOICES,
    )
    is_primary = models.BooleanField(
        help_text="Indicator of whether this is a primary Agreement (and not a component Agreement).",
    )
    version = models.ForeignKey(
        AgreementVersion,
        help_text="The version of the Agreement that was signed.",
        on_delete=models.PROTECT,
    )
    date_signed = models.DateField(
        help_text="Date that this Agreement signed by the institution.",
        default=date.today,
    )
    anvil_access_group = models.OneToOneField(
        ManagedGroup,
        verbose_name=" AnVIL access group",
        on_delete=models.PROTECT,
    )

    history = HistoricalRecords(bases=[SignedAgreementStatusMixin, models.Model])

    def __str__(self):
        return "{}".format(self.cc_id)

    def clean(self):
        if self.type == self.NON_DATA_AFFILIATE and self.is_primary is False:
            raise ValidationError(
                "Non-data affiliate agreements must be primary agreements."
            )

    @property
    def combined_type(self):
        combined_type = self.get_type_display()
        if not self.is_primary:
            combined_type = combined_type + " component"
        return combined_type

    def get_absolute_url(self):
        return self.get_agreement_type().get_absolute_url()

    def get_agreement_type(self):
        if self.type == self.MEMBER:
            return self.memberagreement
        elif self.type == self.DATA_AFFILIATE:
            return self.dataaffiliateagreement
        elif self.type == self.NON_DATA_AFFILIATE:
            return self.nondataaffiliateagreement

    @property
    def agreement_group(self):
        return self.get_agreement_type().get_agreement_group()

    def is_in_cdsa_group(self):
        anvil_cdsa_group = ManagedGroup.objects.get(name=settings.ANVIL_CDSA_GROUP_NAME)
        return GroupGroupMembership.objects.filter(
            parent_group=anvil_cdsa_group,
            child_group=self.anvil_access_group,
        ).exists()


class AgreementTypeModel(models.Model):
    """An abstract model that can be used to provide required fields for agreement type models."""

    # This field should be set by child classes inheriting from this model.
    AGREEMENT_TYPE = None
    ERROR_TYPE_DOES_NOT_MATCH = "The type of the SignedAgreement does not match the expected type for this model."

    signed_agreement = models.OneToOneField(
        SignedAgreement, on_delete=models.CASCADE, primary_key=True
    )
    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.signed_agreement)

    def clean(self):
        """Ensure that the SignedAgreement type is correct for the class."""
        if (
            hasattr(self, "signed_agreement")
            and self.signed_agreement.type != self.AGREEMENT_TYPE
        ):
            raise ValidationError({"signed_agreement": self.ERROR_TYPE_DOES_NOT_MATCH})

    def get_agreement_group(self):
        """Return the group associated with this agreement type."""
        raise NotImplementedError("get_group must be implemented by the subclass.")


class MemberAgreement(TimeStampedModel, AgreementTypeModel, models.Model):
    """A model to hold additional fields for signed member CDSAs."""

    AGREEMENT_TYPE = SignedAgreement.MEMBER

    study_site = models.ForeignKey(
        StudySite,
        on_delete=models.CASCADE,
        help_text="Study Site that this agreement is associated with.",
    )

    def get_absolute_url(self):
        return reverse(
            "cdsa:signed_agreements:members:detail",
            kwargs={"cc_id": self.signed_agreement.cc_id},
        )

    def get_agreement_group(self):
        return self.study_site


class DataAffiliateAgreement(TimeStampedModel, AgreementTypeModel, models.Model):
    """A model to hold additional fields for signed data affiliate CDSAs."""

    AGREEMENT_TYPE = SignedAgreement.DATA_AFFILIATE

    study = models.ForeignKey(
        Study,
        on_delete=models.PROTECT,
        help_text="Study that this agreement is associated with.",
    )
    anvil_upload_group = models.ForeignKey(ManagedGroup, on_delete=models.PROTECT)
    additional_limitations = models.TextField(
        blank=True,
        help_text="Additional limitations on data use as specified in the signed CDSA.",
    )
    requires_study_review = models.BooleanField(
        default=False,
        help_text=(
            "Indicator of whether indicates investigators need to have an approved PRIMED paper proposal "
            "where this dataset was selected and approved in order to work with data brought "
            "under this CDSA."
        ),
    )

    def get_absolute_url(self):
        return reverse(
            "cdsa:signed_agreements:data_affiliates:detail",
            kwargs={"cc_id": self.signed_agreement.cc_id},
        )

    def clean(self):
        super().clean()
        # Checks for fields only allowed for primary agreements.
        if hasattr(self, "signed_agreement") and not self.signed_agreement.is_primary:
            if self.additional_limitations:
                raise ValidationError(
                    "Additional limitations are only allowed for primary agreements."
                )
            if self.requires_study_review:
                raise ValidationError(
                    "requires_study_review can only be True for primary agreements."
                )

    def get_agreement_group(self):
        return self.study


class NonDataAffiliateAgreement(TimeStampedModel, AgreementTypeModel, models.Model):
    """A model to hold additional fields for signed non-data affiliate CDSAs."""

    AGREEMENT_TYPE = SignedAgreement.NON_DATA_AFFILIATE

    affiliation = models.CharField(
        max_length=255, help_text="The affiliation of the person signing this CDSA."
    )

    def get_absolute_url(self):
        return reverse(
            "cdsa:signed_agreements:non_data_affiliates:detail",
            kwargs={"cc_id": self.signed_agreement.cc_id},
        )

    def get_agreement_group(self):
        return self.affiliation


class CDSAWorkspace(
    TimeStampedModel, RequesterModel, DataUseOntologyModel, BaseWorkspaceData
):
    """A model to track additional data about a CDSA workspace."""

    # Only one study per workspace.
    study = models.ForeignKey(
        Study,
        on_delete=models.PROTECT,
        help_text="The study associated with data in this workspace.",
    )
    additional_limitations = models.TextField(
        help_text="""Additional data use limitations that cannot be captured by DUO.""",
        blank=True,
    )
    acknowledgments = models.TextField(
        help_text="Acknowledgments associated with data in this workspace."
    )
    available_data = models.ManyToManyField(
        AvailableData,
        help_text="Data available in this accession.",
        blank=True,
    )
    gsr_restricted = models.BooleanField(
        verbose_name="GSR restricted?",
        help_text="Indicator of whether public posting of GSRs is restricted.",
    )

    class Meta:
        verbose_name = " CDSA workspace"
        verbose_name_plural = " CDSA workspaces"

    def get_primary_cdsa(self):
        """Return the primary, valid CDSA associated with this workspace."""
        cdsa = DataAffiliateAgreement.objects.get(
            study=self.study,
            signed_agreement__is_primary=True,
            signed_agreement__status=SignedAgreement.StatusChoices.ACTIVE,
        )
        return cdsa
