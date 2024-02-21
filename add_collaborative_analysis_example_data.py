"""Temporary script to create some example data for the collaborative_analysis app.

Run with: python manage.py shell < add_collaborative_analysis_example_data.py
"""

from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    BillingProjectFactory,
    GroupAccountMembershipFactory,
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
)

from primed.cdsa.tests.factories import CDSAWorkspaceFactory
from primed.collaborative_analysis.tests.factories import (
    CollaborativeAnalysisWorkspaceFactory,
)
from primed.dbgap.tests.factories import dbGaPWorkspaceFactory
from primed.miscellaneous_workspaces.tests.factories import OpenAccessWorkspaceFactory

billing_project = BillingProjectFactory.create(name="test_collab")

# Create some collaborative analysis workspace.
# Workspace 1
collaborative_analysis_workspace_1 = CollaborativeAnalysisWorkspaceFactory.create(
    workspace__name="collab_1_open_access", workspace__billing_project=billing_project
)
source_workspace_1_1 = OpenAccessWorkspaceFactory.create(
    workspace__name="source_1_open_access", workspace__billing_project=billing_project
)
collaborative_analysis_workspace_1.source_workspaces.add(source_workspace_1_1.workspace)

# Workspace 2
collaborative_analysis_workspace_2 = CollaborativeAnalysisWorkspaceFactory.create(
    workspace__name="collab_2_dbgap_and_cdsa",
    workspace__billing_project=billing_project,
)
source_workspace_2_1 = dbGaPWorkspaceFactory.create(
    workspace__name="source_2_dbgap", workspace__billing_project=billing_project
)
collaborative_analysis_workspace_2.source_workspaces.add(source_workspace_2_1.workspace)
source_workspace_2_2 = CDSAWorkspaceFactory.create(
    workspace__name="source_2_cdsa", workspace__billing_project=billing_project
)
collaborative_analysis_workspace_2.source_workspaces.add(source_workspace_2_2.workspace)

# Workspace 3 - with an error
collaborative_analysis_workspace_3 = CollaborativeAnalysisWorkspaceFactory.create(
    workspace__name="collab_3_with_error", workspace__billing_project=billing_project
)
source_workspace_3_1 = OpenAccessWorkspaceFactory.create(
    workspace__name="source_3_open_access", workspace__billing_project=billing_project
)
collaborative_analysis_workspace_3.source_workspaces.add(source_workspace_3_1.workspace)


# Add accounts to the auth domains.
account_1 = AccountFactory.create(
    user__name="Adrienne", verified=True, email="adrienne@example.com"
)
account_2 = AccountFactory.create(
    user__name="Ben", verified=True, email="ben@example.com"
)
account_3 = AccountFactory.create(
    user__name="Matt", verified=True, email="matt@example.com"
)
account_4 = AccountFactory.create(
    user__name="Stephanie", verified=True, email="stephanie@example.com"
)

# Set up collab analysis workspace one
# analyst group
GroupAccountMembershipFactory.create(
    account=account_1, group=collaborative_analysis_workspace_1.analyst_group
)
GroupAccountMembershipFactory.create(
    account=account_2, group=collaborative_analysis_workspace_1.analyst_group
)
# auth domains
GroupAccountMembershipFactory.create(
    account=account_1,
    group=collaborative_analysis_workspace_1.workspace.authorization_domains.first(),
)

# Set up collab analysis workspace two
# analyst group
GroupAccountMembershipFactory.create(
    account=account_3, group=collaborative_analysis_workspace_2.analyst_group
)
GroupAccountMembershipFactory.create(
    account=account_4, group=collaborative_analysis_workspace_2.analyst_group
)
# auth domains
GroupAccountMembershipFactory.create(
    account=account_3,
    group=collaborative_analysis_workspace_2.workspace.authorization_domains.first(),
)
GroupAccountMembershipFactory.create(
    account=account_3,
    group=source_workspace_2_1.workspace.authorization_domains.first(),
)
GroupAccountMembershipFactory.create(
    account=account_3,
    group=source_workspace_2_2.workspace.authorization_domains.first(),
)
GroupAccountMembershipFactory.create(
    account=account_4,
    group=source_workspace_2_1.workspace.authorization_domains.first(),
)

# Set up collab analysis workspace three
# Managed group to show an error
managed_group = ManagedGroupFactory.create(name="test-error")
GroupGroupMembershipFactory.create(
    parent_group=collaborative_analysis_workspace_3.workspace.authorization_domains.first(),
    child_group=managed_group,
)
