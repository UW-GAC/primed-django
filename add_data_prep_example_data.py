# Temporary script to create some test data.
# Run with: python manage.py shell < add_data_prep_example_data.py


from primed.cdsa.tests.factories import CDSAWorkspaceFactory
from primed.dbgap.tests.factories import dbGaPWorkspaceFactory
from primed.miscellaneous_workspaces.tests import factories
from primed.primed_anvil.tests.factories import StudyFactory

# Create a dbGaP workspace.
fhs = StudyFactory.create(short_name="FHS", full_name="Framingham Heart Study")
workspace_dbgap = dbGaPWorkspaceFactory.create(
    dbgap_study_accession__dbgap_phs=7,
    dbgap_study_accession__studies=[fhs],
    dbgap_version=33,
    dbgap_participant_set=12,
    dbgap_consent_code=1,
    dbgap_consent_abbreviation="HMB",
    workspace__name="DBGAP_FHS_v33_p12_HMB",
)

# Create a data prep workspace.
workspace_dbgap_prep = factories.DataPrepWorkspaceFactory.create(
    target_workspace=workspace_dbgap.workspace,
    workspace__name="DBGAP_FHS_v33_p12_HMB_PREP",
)


# Create a CDSA workspace.
workspace_cdsa = CDSAWorkspaceFactory.create(
    study__short_name="MESA",
    workspace__name="CDSA_MESA_HMB",
)

# Create a data prep workspace.
factories.DataPrepWorkspaceFactory.create(
    target_workspace=workspace_cdsa.workspace,
    workspace__name="CDSA_MESA_HMB_PREP_1",
    is_active=False,
)
workspace_cdsa_prep = factories.DataPrepWorkspaceFactory.create(
    target_workspace=workspace_cdsa.workspace,
    workspace__name="CDSA_MESA_HMB_PREP_2",
)
