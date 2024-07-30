# Temporary script to create some test data.
# Run with: python manage.py shell < add_inventory_input_example_data.py

from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceGroupSharingFactory,
)

from primed.cdsa.tests.factories import CDSAWorkspaceFactory
from primed.dbgap.tests.factories import dbGaPWorkspaceFactory
from primed.miscellaneous_workspaces.tests.factories import OpenAccessWorkspaceFactory
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


# Create a CDSA workspace.
workspace_cdsa = CDSAWorkspaceFactory.create(
    study__short_name="MESA",
    workspace__name="CDSA_MESA_HMB",
)

# Create an open access workspace
workspace_open_access = OpenAccessWorkspaceFactory.create(
    workspace__name="OPEN_ACCESS_FHS",
)
workspace_open_access.studies.add(fhs)


# Share workspaces with PRIMED_ALL
primed_all = ManagedGroupFactory.create(name="PRIMED_ALL")
WorkspaceGroupSharingFactory.create(workspace=workspace_dbgap.workspace, group=primed_all)
WorkspaceGroupSharingFactory.create(workspace=workspace_cdsa.workspace, group=primed_all)
WorkspaceGroupSharingFactory.create(workspace=workspace_open_access.workspace, group=primed_all)
