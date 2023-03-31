from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceFactory,
)
from factory import (  # Dict,; DictFactory,; LazyAttribute,; List,; SelfAttribute,; Trait,; post_generation,
    Faker,
    LazyAttribute,
    Sequence,
    SubFactory,
)
from factory.django import DjangoModelFactory

from primed.duo.tests.factories import DataUsePermissionFactory
from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
from primed.users.tests.factories import UserFactory

from .. import models


class CDSAFactory(DjangoModelFactory):
    """A factory for the CDSA model."""

    cc_id = Sequence(lambda n: n + 1001)
    representative = SubFactory(UserFactory)
    institution = Faker("company")
    type = models.CDSA.MEMBER
    is_component = False
    representative_role = Faker("job")
    anvil_access_group = SubFactory(
        ManagedGroupFactory,
        name=LazyAttribute(
            lambda o: "PRIMED_CDSA_ACCESS_{}".format(o.factory_parent.cc_id)
        ),
    )

    class Meta:
        model = models.CDSA


class MemberFactory(DjangoModelFactory):

    cdsa = SubFactory(CDSAFactory, type=models.CDSA.MEMBER)
    study_site = SubFactory(StudySiteFactory)

    class Meta:
        model = models.Member


class DataAffiliateFactory(DjangoModelFactory):

    cdsa = SubFactory(CDSAFactory, type=models.CDSA.DATA_AFFILIATE)
    study = SubFactory(StudyFactory)

    class Meta:
        model = models.DataAffiliate


class NonDataAffiliateFactory(DjangoModelFactory):

    cdsa = SubFactory(CDSAFactory, type=models.CDSA.NON_DATA_AFFILIATE)
    study_or_center = Faker("company")

    class Meta:
        model = models.NonDataAffiliate


class CDSAWorkspaceFactory(DjangoModelFactory):
    """A factory for the CDSAWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="cdsa")
    requested_by = SubFactory(UserFactory)
    cdsa = SubFactory(DataAffiliateFactory)
    data_use_permission = SubFactory(DataUsePermissionFactory)
    data_use_limitations = Faker("paragraph", nb_sentences=5)
    acknowledgments = Faker("paragraph")

    class Meta:
        model = models.CDSAWorkspace
