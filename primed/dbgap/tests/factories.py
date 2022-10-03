from anvil_consortium_manager.tests.factories import WorkspaceFactory
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from primed.primed_anvil.tests.factories import (
    DataUseOntologyModelFactory,
    StudyFactory,
)
from primed.users.tests.factories import UserFactory

from .. import models


class dbGaPStudyAccessionFactory(DjangoModelFactory):
    """A factory for the dbGaPStudy model."""

    study = SubFactory(StudyFactory)
    phs = Faker("random_int")

    class Meta:
        model = models.dbGaPStudyAccession


class dbGaPWorkspaceFactory(DataUseOntologyModelFactory):
    """A factory for the dbGaPWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="dbgap")
    dbgap_study_accession = SubFactory(dbGaPStudyAccessionFactory)
    dbgap_version = Faker("random_int")
    dbgap_participant_set = Faker("random_int")
    # Ideally we would calculate the default full consent code from the data use permission and limitations,
    # but that is not straightforward and it doesn't particularly matter.
    full_consent_code = Faker("word")
    data_use_limitations = Faker("paragraph")

    class Meta:
        model = models.dbGaPWorkspace


class dbGaPApplicationFactory(DjangoModelFactory):
    """A factory for the dbGaPApplication model."""

    principal_investigator = SubFactory(UserFactory)
    project_id = Faker("random_int")

    class Meta:
        model = models.dbGaPApplication


class dbGaPDataAccessRequestFactory(DjangoModelFactory):
    """A factory for the dbGaPApplication model."""

    dbgap_application = SubFactory(dbGaPApplicationFactory)
    dbgap_study_accession = SubFactory(dbGaPStudyAccessionFactory)
    dbgap_dar_id = Faker("random_int")
    dbgap_version = Faker("random_int")
    dbgap_participant_set = Faker("random_int")
    dbgap_consent_code = Faker("random_int")
    dbgap_consent_abbreviation = Faker("word")

    class Meta:
        model = models.dbGaPDataAccessRequest
