from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceFactory,
)
from factory import Dict, Faker, SelfAttribute, SubFactory
from factory.django import DjangoModelFactory

from primed.primed_anvil.tests.factories import (
    DataUseOntologyModelFactory,
    StudyFactory,
)
from primed.users.tests.factories import UserFactory

from .. import models


class TimeStampedModelFactory(DjangoModelFactory):
    """A factory that allows `created` to be set to some specified value."""

    class Meta:
        abstract = True

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        created = kwargs.pop("created", None)
        obj = super()._create(target_class, *args, **kwargs)
        if created:
            obj.created = created
            obj.save()
        return obj


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
    dbgap_consent_code = Faker("random_int")
    dbgap_consent_abbreviation = Faker("word")
    data_use_limitations = Faker("paragraph")

    class Meta:
        model = models.dbGaPWorkspace


class dbGaPApplicationFactory(DjangoModelFactory):
    """A factory for the dbGaPApplication model."""

    principal_investigator = SubFactory(UserFactory)
    dbgap_project_id = Faker("random_int")
    anvil_group = SubFactory(ManagedGroupFactory)

    class Meta:
        model = models.dbGaPApplication


class dbGaPDataAccessSnapshotFactory(TimeStampedModelFactory, DjangoModelFactory):
    """A factory for the dbGaPDataAccessSnapshot model."""

    dbgap_application = SubFactory(dbGaPApplicationFactory)
    # From docs, need to use the .. syntax with a Dict:
    # https://factoryboy.readthedocs.io/en/stable/reference.html#factory.Dict
    dbgap_dar_data = Dict(
        {
            "Project_id": SelfAttribute("..dbgap_application.dbgap_project_id"),
            "PI_name": Faker("name"),
            "Project_closed": "no",
            "studies": [],
        }
    )

    class Meta:
        model = models.dbGaPDataAccessSnapshot


class dbGaPDataAccessRequestFactory(DjangoModelFactory):
    """A factory for the dbGaPApplication model."""

    dbgap_data_access_snapshot = SubFactory(dbGaPDataAccessSnapshotFactory)
    dbgap_phs = Faker("random_int")
    dbgap_dar_id = Faker("random_int")
    original_version = Faker("random_int")
    original_participant_set = Faker("random_int")
    dbgap_consent_code = Faker("random_int")
    dbgap_consent_abbreviation = Faker("word")
    dbgap_current_status = models.dbGaPDataAccessRequest.APPROVED

    class Meta:
        model = models.dbGaPDataAccessRequest
