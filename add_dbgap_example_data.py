# Temporary script to create some test data.
# Run with: python manage.py shell < add_cdsa_example_data.py

from anvil_consortium_manager.tests.factories import GroupGroupMembershipFactory

from primed.dbgap import models
from primed.dbgap.tests import factories
from primed.primed_anvil.tests.factories import StudyFactory
from primed.users.tests.factories import UserFactory

# Studies
fhs = StudyFactory.create(short_name="FHS", full_name="Framingham Heart Study")
mesa = StudyFactory.create(short_name="MESA", full_name="Multi-Ethnic Study of Atherosclerosis")
aric = StudyFactory.create(short_name="ARIC", full_name="Atherosclerosis Risk in Communities")

# dbGaP study accessions
dbgap_study_accession_fhs = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=7, studies=[fhs])
dbgap_study_accession_mesa = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=209, studies=[mesa])
dbgap_study_accession_aric = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=280, studies=[aric])


# Create some dbGaP workspaces.
workspace_fhs_1 = factories.dbGaPWorkspaceFactory.create(
    dbgap_study_accession=dbgap_study_accession_fhs,
    dbgap_version=33,
    dbgap_participant_set=12,
    dbgap_consent_code=1,
    dbgap_consent_abbreviation="HMB",
    workspace__name="DBGAP_FHS_v33_p12_HMB",
)
workspace_fhs_2 = factories.dbGaPWorkspaceFactory.create(
    dbgap_study_accession=dbgap_study_accession_fhs,
    dbgap_version=33,
    dbgap_participant_set=12,
    dbgap_consent_code=2,
    dbgap_consent_abbreviation="GRU",
    workspace__name="DBGAP_FHS_v33_p12_GRU",
)
workspace_mesa_1 = factories.dbGaPWorkspaceFactory.create(
    dbgap_study_accession=dbgap_study_accession_mesa,
    dbgap_version=2,
    dbgap_participant_set=1,
    dbgap_consent_code=1,
    dbgap_consent_abbreviation="HMB-NPU",
    workspace__name="DBGAP_MESA_v2_p1_HMB-NPU",
)
workspace_mesa_2 = factories.dbGaPWorkspaceFactory.create(
    dbgap_study_accession=dbgap_study_accession_mesa,
    dbgap_version=2,
    dbgap_participant_set=1,
    dbgap_consent_code=2,
    dbgap_consent_abbreviation="HMB-NPU-IRB",
    workspace__name="DBGAP_MESA_v2_p1_HMB-NPU-IRB",
)
workspace_aric = factories.dbGaPWorkspaceFactory.create(
    dbgap_study_accession=dbgap_study_accession_aric,
    dbgap_version=3,
    dbgap_participant_set=1,
    dbgap_consent_code=1,
    dbgap_consent_abbreviation="HMB",
    workspace__name="DBGAP_ARIC_v3_p1_HMB",
)


# Create some dbGaP applications
dbgap_application_1 = factories.dbGaPApplicationFactory.create(
    principal_investigator=UserFactory.create(name="Ken", username="Ken"),
    dbgap_project_id=33119,
)
# Add a snapshot
dar_snapshot_1 = factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=dbgap_application_1)
# Add some data access requests.
dar_1_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
    dbgap_workspace=workspace_fhs_1,
    dbgap_data_access_snapshot=dar_snapshot_1,
    dbgap_dac="NHLBI",
    dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
)
dar_1_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
    dbgap_workspace=workspace_fhs_2,
    dbgap_data_access_snapshot=dar_snapshot_1,
    dbgap_dac="NHLBI",
    dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
)
dar_1_3 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
    dbgap_workspace=workspace_mesa_1,
    dbgap_data_access_snapshot=dar_snapshot_1,
    dbgap_dac="NHLBI",
    dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
)
dar_1_4 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
    dbgap_workspace=workspace_mesa_2,
    dbgap_data_access_snapshot=dar_snapshot_1,
    dbgap_dac="NHLBI",
    dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
)
dar_1_5 = factories.dbGaPDataAccessRequestFactory(
    dbgap_data_access_snapshot=dar_snapshot_1,
    dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
)

dbgap_application_2 = factories.dbGaPApplicationFactory.create(
    principal_investigator=UserFactory.create(name="Alisa", username="Alisa"),
    dbgap_project_id=33371,
)
# Add a snapshot
dar_snapshot_2 = factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=dbgap_application_2)
# Add some data access requests, only for FHS.
dar_1_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
    dbgap_workspace=workspace_fhs_1,
    dbgap_data_access_snapshot=dar_snapshot_2,
    dbgap_dac="NHLBI",
    dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
)
dar_1_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
    dbgap_workspace=workspace_fhs_2,
    dbgap_data_access_snapshot=dar_snapshot_2,
    dbgap_dac="NHLBI",
    dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
)

# Now add dbGaP access groups.
GroupGroupMembershipFactory.create(
    parent_group=workspace_fhs_1.workspace.authorization_domains.first(),
    child_group=dbgap_application_1.anvil_access_group,
)
