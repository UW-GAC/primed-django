# Temporary script to create some test data.
# Run with: python manage.py shell < add_cdsa_test_data.py

from anvil_consortium_manager.models import ManagedGroup
from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
    WorkspaceGroupSharingFactory,
)

from primed.cdsa import models
from primed.cdsa.tests import factories
from primed.duo.tests.factories import DataUseModifierFactory, DataUsePermissionFactory
from primed.users.tests.factories import UserFactory

# Create a couple signed CDSAs.
dup = DataUsePermissionFactory.create(abbreviation="GRU")
dum = DataUseModifierFactory.create(abbreviation="NPU")

# create the CDSA auth group
cdsa_auth_group = ManagedGroupFactory.create(name="AUTH_PRIMED_CDSA")


# Create some CDSAs
cdsa_1001 = factories.CDSAFactory.create(
    cc_id=1001,
    representative=UserFactory.create(name="Ken Rice"),
    institution="UW",
    group="CC",
    representative_role="Contact PI",
    type=models.CDSA.MEMBER,
    is_component=False,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1001.anvil_access_group
)

cdsa_1002 = factories.CDSAFactory.create(
    cc_id=1002,
    representative=UserFactory.create(name="Sally Adebamowo"),
    institution="UM",
    group="CARDINAL",
    representative_role="Contact PI",
    type=models.CDSA.MEMBER,
    is_component=False,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1002.anvil_access_group
)

cdsa_1003 = factories.CDSAFactory.create(
    cc_id=1003,
    representative=UserFactory.create(name="Bamidele Adebamowo"),
    institution="Loyola",
    group="CARDINAL",
    representative_role="Co-PI",
    type=models.CDSA.MEMBER,
    is_component=True,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1003.anvil_access_group
)

cdsa_1004 = factories.CDSAFactory.create(
    cc_id=1004,
    representative=UserFactory.create(name="Brackie Mitchell"),
    institution="UM",
    group="CARDINAL",
    representative_role="Co-I",
    type=models.CDSA.MEMBER,
    is_component=True,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1004.anvil_access_group
)

cdsa_1005 = factories.CDSAFactory.create(
    cc_id=1005,
    representative=UserFactory.create(name="Brackie Mitchell"),
    institution="UMaryland",
    group="Amish",
    representative_role="Study PI",
    type=models.CDSA.DATA_AFFILIATE,
    is_component=False,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1005.anvil_access_group
)

cdsa_1006 = factories.CDSAFactory.create(
    cc_id=1006,
    representative=UserFactory.create(name="Robyn"),
    institution="UW",
    group="MESA",
    representative_role="DCC PI",
    type=models.CDSA.DATA_AFFILIATE,
    is_component=False,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1006.anvil_access_group
)

cdsa_1007 = factories.CDSAFactory.create(
    cc_id=1007,
    representative=UserFactory.create(name="Wendy"),
    institution="JHU",
    group="MESA",
    representative_role="Field Center PI",
    type=models.CDSA.DATA_AFFILIATE,
    is_component=True,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1007.anvil_access_group
)

cdsa_1008 = factories.CDSAFactory.create(
    cc_id=1008,
    representative=UserFactory.create(name="Jerry"),
    institution="Lundquist",
    group="MESA",
    representative_role="Analysis Center PI",
    type=models.CDSA.DATA_AFFILIATE,
    is_component=True,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1008.anvil_access_group
)

cdsa_1009 = factories.CDSAFactory.create(
    cc_id=1009,
    representative=UserFactory.create(name="ExpertA"),
    institution="UABC",
    group="CenterXYZ",
    representative_role="Contact PI",
    type=models.CDSA.NON_DATA_AFFILIATE,
    is_component=False,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1009.anvil_access_group
)


# Add some users to the CDSA groups.
accounts = AccountFactory.create_batch(10, verified=True)
GroupAccountMembershipFactory.create(
    group=cdsa_1001.anvil_access_group, account=accounts[0]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1001.anvil_access_group, account=accounts[1]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1001.anvil_access_group, account=accounts[2]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1002.anvil_access_group, account=accounts[3]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1002.anvil_access_group, account=accounts[4]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1003.anvil_access_group, account=accounts[5]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1005.anvil_access_group, account=accounts[6]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1005.anvil_access_group, account=accounts[7]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1006.anvil_access_group, account=accounts[8]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1006.anvil_access_group, account=accounts[9]
)

cdsa_workspace_1 = factories.CDSAWorkspaceFactory.create(
    cdsa=cdsa_1006,
    study__full_name=cdsa_1006.group,
    study__short_name=cdsa_1006.group,
    data_use_permission=dup,
)
cdsa_workspace_1.workspace.authorization_domains.add(cdsa_auth_group)

# Share with primed_all.
primed_all_group = ManagedGroup.objects.get(name="PRIMED_ALL")
WorkspaceGroupSharingFactory.create(
    group=primed_all_group, workspace=cdsa_workspace_1.workspace
)

# Create a second workspace that is not shared.
cdsa_workspace_2 = factories.CDSAWorkspaceFactory.create(
    cdsa=cdsa_1006,
    study=cdsa_workspace_1.study,
    data_use_permission=dup,
)
cdsa_workspace_2.workspace.authorization_domains.add(cdsa_auth_group)
cdsa_workspace_2.data_use_modifiers.add(dum)
