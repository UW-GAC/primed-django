from anvil_consortium_manager.tests.factories import WorkspaceFactory
from factory import Faker, SubFactory

from primed.primed_anvil.tests.factories import (
    DataUseOntologyModelFactory,
    StudyFactory,
)

from .. import models


class dbGaPWorkspaceFactory(DataUseOntologyModelFactory):
    """A factory for the dbGaPWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="dbgap")
    study = SubFactory(StudyFactory)
    # Ideally we would calculate the default full consent code from the data use permission and limitations,
    # but that is not straightforward and it doesn't particularly matter.
    full_consent_code = Faker("word")
    phs = Faker("random_int")
    version = Faker("random_int")
    participant_set = Faker("random_int")

    class Meta:
        model = models.dbGaPWorkspace
