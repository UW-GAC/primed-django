from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceFactory,
)
from django.conf import settings
from factory import Faker, LazyAttribute, Sequence, SubFactory, post_generation
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from primed.duo.tests.factories import DataUsePermissionFactory
from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
from primed.users.tests.factories import UserFactory

from .. import models


class AgreementMajorVersionFactory(DjangoModelFactory):
    """A factory for the AgreementMajorVersion model."""

    class Meta:
        model = models.AgreementMajorVersion
        django_get_or_create = ("version",)

    version = Faker("random_int", min=1)


class AgreementVersionFactory(DjangoModelFactory):
    """A factory for the AgreementVersion model."""

    class Meta:
        model = models.AgreementVersion

    major_version = SubFactory(AgreementMajorVersionFactory)
    minor_version = Faker("random_int")
    date_approved = Faker("date")


class SignedAgreementFactory(DjangoModelFactory):
    """A factory for the SignedAgreement model."""

    cc_id = Sequence(lambda n: n + 1001)
    representative = SubFactory(UserFactory)
    representative_role = Faker("job")
    signing_institution = Faker("company")
    type = FuzzyChoice(
        models.SignedAgreement.TYPE_CHOICES,
        getter=lambda c: c[0],
    )
    # Assume is_primary=True for now.
    is_primary = True
    version = SubFactory(AgreementVersionFactory)
    date_signed = Faker("date")
    anvil_access_group = SubFactory(
        ManagedGroupFactory,
        name=LazyAttribute(
            lambda o: settings.ANVIL_DATA_ACCESS_GROUP_PREFIX
            + "_CDSA_ACCESS_"
            + str(o.factory_parent.cc_id)
        ),
    )

    class Meta:
        model = models.SignedAgreement


class MemberAgreementFactory(DjangoModelFactory):

    signed_agreement = SubFactory(
        SignedAgreementFactory, type=models.SignedAgreement.MEMBER
    )
    study_site = SubFactory(StudySiteFactory)

    class Meta:
        model = models.MemberAgreement


class DataAffiliateAgreementFactory(DjangoModelFactory):

    signed_agreement = SubFactory(
        SignedAgreementFactory, type=models.SignedAgreement.DATA_AFFILIATE
    )
    study = SubFactory(StudyFactory)
    anvil_upload_group = SubFactory(
        ManagedGroupFactory,
        name=LazyAttribute(
            lambda o: settings.ANVIL_DATA_ACCESS_GROUP_PREFIX
            + "_CDSA_UPLOAD_"
            + str(o.factory_parent.signed_agreement.cc_id)
        ),
    )

    class Meta:
        model = models.DataAffiliateAgreement


class NonDataAffiliateAgreementFactory(DjangoModelFactory):

    signed_agreement = SubFactory(
        SignedAgreementFactory, type=models.SignedAgreement.NON_DATA_AFFILIATE
    )
    affiliation = Faker("company")

    class Meta:
        model = models.NonDataAffiliateAgreement


class CDSAWorkspaceFactory(DjangoModelFactory):

    study = SubFactory(StudyFactory)
    data_use_limitations = Faker("paragraph")
    acknowledgments = Faker("paragraph")
    requested_by = SubFactory(UserFactory)
    data_use_permission = SubFactory(DataUsePermissionFactory)
    workspace = SubFactory(WorkspaceFactory, workspace_type="cdsa")

    @post_generation
    def authorization_domains(self, create, extracted, **kwargs):
        # Add an authorization domain.
        if not create:
            # Simple build, do nothing.
            return

        # Create an authorization domain.
        auth_domain = ManagedGroupFactory.create()
        self.workspace.authorization_domains.add(auth_domain)

    class Meta:
        model = models.CDSAWorkspace
        skip_postgeneration_save = True
