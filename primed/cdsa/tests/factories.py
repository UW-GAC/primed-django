from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceFactory,
)
from factory import (  # Dict,; DictFactory,; LazyAttribute,; List,; SelfAttribute,; Trait,; post_generation,
    Faker,
    Sequence,
    SubFactory,
)
from factory.django import DjangoModelFactory

from primed.primed_anvil.tests.factories import StudyFactory
from primed.users.tests.factories import UserFactory

from .. import models


class CDSAFactory(DjangoModelFactory):
    """A factory for the CDSA model."""

    cc_id = Sequence(lambda n: n + 1001)
    representative = SubFactory(UserFactory)
    institution = Faker("company")
    group = Faker("company")
    type = models.CDSA.MEMBER
    is_component = False
    representative_role = Faker("job")
    anvil_access_group = SubFactory(ManagedGroupFactory)

    class Meta:
        model = models.CDSA


class CDSAWorkspaceFactory(DjangoModelFactory):
    """A factory for the CDSAWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="cdsa")
    requested_by = SubFactory(UserFactory)
    cdsa = SubFactory(CDSAFactory)
    study = SubFactory(StudyFactory)

    data_use_limitations = Faker("paragraph")
    acknowledgments = Faker("paragraph")
