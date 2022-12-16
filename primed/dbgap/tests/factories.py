from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceFactory,
)
from factory import (
    Dict,
    DictFactory,
    Faker,
    LazyAttribute,
    List,
    SelfAttribute,
    Sequence,
    SubFactory,
    Trait,
    post_generation,
)
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from primed.primed_anvil.tests.factories import (
#    DataUseOntologyModelFactory,
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

    dbgap_phs = Sequence(lambda n: n)

    @post_generation
    def studies(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for study in extracted:
                self.studies.add(study)
        else:
            # Create a study and save it.
            study = StudyFactory.create()
            self.studies.add(study)

    class Meta:
        model = models.dbGaPStudyAccession


class dbGaPWorkspaceFactory(TimeStampedModelFactory, DjangoModelFactory):  # DataUseOntologyModelFactory):
    """A factory for the dbGaPWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="dbgap")
    dbgap_study_accession = SubFactory(dbGaPStudyAccessionFactory)
    dbgap_version = Faker("random_int")
    dbgap_participant_set = Faker("random_int")
    dbgap_consent_code = Faker("random_int")
    dbgap_consent_abbreviation = Faker("word")
    data_use_limitations = Faker("paragraph")
    acknowledgments = Faker("paragraph")
    requested_by = SubFactory(UserFactory)

    class Meta:
        model = models.dbGaPWorkspace


class dbGaPApplicationFactory(DjangoModelFactory):
    """A factory for the dbGaPApplication model."""

    principal_investigator = SubFactory(UserFactory)
    dbgap_project_id = Sequence(lambda n: n)
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
    is_most_recent = True

    class Meta:
        model = models.dbGaPDataAccessSnapshot


class dbGaPDataAccessRequestFactory(DjangoModelFactory):
    """A factory for the dbGaPApplication model."""

    dbgap_data_access_snapshot = SubFactory(dbGaPDataAccessSnapshotFactory)
    dbgap_phs = Faker("random_int")
    dbgap_dar_id = Sequence(lambda n: n)
    original_version = Faker("random_int")
    original_participant_set = Faker("random_int")
    dbgap_consent_code = Faker("random_int")
    dbgap_consent_abbreviation = Faker("word")
    dbgap_current_status = models.dbGaPDataAccessRequest.APPROVED
    dbgap_dac = Faker("word")

    class Meta:
        model = models.dbGaPDataAccessRequest


class dbGaPDataAccessRequestForWorkspaceFactory(DjangoModelFactory):
    """A factory for the dbGaPApplication model to match a workspace."""

    dbgap_data_access_snapshot = SubFactory(dbGaPDataAccessSnapshotFactory)
    dbgap_phs = LazyAttribute(
        lambda o: o.dbgap_workspace.dbgap_study_accession.dbgap_phs
    )
    dbgap_dar_id = Sequence(lambda n: n)
    original_version = LazyAttribute(lambda o: o.dbgap_workspace.dbgap_version)
    original_participant_set = LazyAttribute(
        lambda o: o.dbgap_workspace.dbgap_participant_set
    )
    dbgap_consent_code = LazyAttribute(lambda o: o.dbgap_workspace.dbgap_consent_code)
    dbgap_consent_abbreviation = Faker("word")
    dbgap_current_status = models.dbGaPDataAccessRequest.APPROVED
    dbgap_dac = Faker("word")

    class Params:
        dbgap_workspace = None

    class Meta:
        model = models.dbGaPDataAccessRequest


class dbGaPJSONRequestFactory(DictFactory):
    """Factory to create JSON for a data access request associated with a study."""

    DAC_abbrev = Faker("word")
    consent_abbrev = Faker("word")
    consent_code = Faker("random_int")
    DAR = Sequence(lambda n: n)
    current_version = Faker("random_int")
    current_DAR_status = FuzzyChoice(
        models.dbGaPDataAccessRequest.DBGAP_CURRENT_STATUS_CHOICES,
        getter=lambda c: c[0],
    )
    was_approved = "yes"


class dbGaPJSONStudyFactory(DictFactory):
    """Factory to create JSON for studies associated with a project."""

    study_name = Faker("company")
    study_accession = Faker("numerify", text="phs######")
    requests = List([SubFactory(dbGaPJSONRequestFactory)])


class dbGaPJSONProjectFactory(DictFactory):
    """Factory to create JSON a project."""

    Project_id = Sequence(lambda n: n)
    PI_name = Faker("name")
    Project_closed = "no"
    studies = List([SubFactory(dbGaPJSONStudyFactory)])

    class Params:
        dbgap_application = Trait(
            Project_id=LazyAttribute(lambda o: o.dbgap_application.dbgap_project_id)
        )
