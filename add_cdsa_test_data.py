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
from primed.primed_anvil.models import StudySite
from primed.users.tests.factories import UserFactory

# Create a couple signed CDSAs.
dup = DataUsePermissionFactory.create(abbreviation="GRU")
dum = DataUseModifierFactory.create(abbreviation="NPU")

# create the CDSA auth group
cdsa_auth_group = ManagedGroupFactory.create(name="AUTH_PRIMED_CDSA")


# Create some CDSAs
cdsa_1001 = factories.MemberFactory.create(
    cdsa__cc_id=1001,
    cdsa__representative=UserFactory.create(name="Ken Rice"),
    cdsa__institution="UW",
    cdsa__representative_role="Contact PI",
    study_site=StudySite.objects.get(short_name="CC"),
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1001.cdsa.anvil_access_group
)

cdsa_1002 = factories.MemberFactory.create(
    cdsa__cc_id=1002,
    cdsa__representative=UserFactory.create(name="Sally Adebamowo"),
    cdsa__institution="UM",
    study_site__short_name="CARDINAL",
    cdsa__representative_role="Contact PI",
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1002.cdsa.anvil_access_group
)

cdsa_1003 = factories.MemberComponentFactory.create(
    cdsa__cc_id=1003,
    cdsa__representative=UserFactory.create(name="Bamidele Tayo"),
    cdsa__institution="Loyola",
    component_of=cdsa_1002,
    cdsa__representative_role="Co-PI",
    cdsa__type=models.CDSA.MEMBER_COMPONENT,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1003.cdsa.anvil_access_group
)

cdsa_1004 = factories.MemberComponentFactory.create(
    cdsa__cc_id=1004,
    cdsa__representative=UserFactory.create(name="Brackie Mitchell"),
    cdsa__institution="UM",
    cdsa__representative_role="Co-I",
    component_of=cdsa_1002,
    cdsa__type=models.CDSA.MEMBER_COMPONENT,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1004.cdsa.anvil_access_group
)

cdsa_1005 = factories.DataAffiliateFactory.create(
    cdsa__cc_id=1005,
    cdsa__representative=UserFactory.create(name="Brackie Mitchell"),
    cdsa__institution="UMaryland",
    study__short_name="Amish",
    cdsa__representative_role="Study PI",
    cdsa__type=models.CDSA.DATA_AFFILIATE,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1005.cdsa.anvil_access_group
)

cdsa_1006 = factories.DataAffiliateFactory.create(
    cdsa__cc_id=1006,
    cdsa__representative=UserFactory.create(name="Robyn"),
    cdsa__institution="UW",
    study__short_name="MESA",
    cdsa__representative_role="DCC PI",
    cdsa__type=models.CDSA.DATA_AFFILIATE,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1006.cdsa.anvil_access_group
)

cdsa_1007 = factories.DataAffiliateComponentFactory.create(
    cdsa__cc_id=1007,
    cdsa__representative=UserFactory.create(name="Wendy"),
    cdsa__institution="JHU",
    cdsa__representative_role="Field Center PI",
    component_of=cdsa_1006,
    cdsa__type=models.CDSA.DATA_AFFILIATE_COMPONENT,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1007.cdsa.anvil_access_group
)

cdsa_1008 = factories.DataAffiliateComponentFactory.create(
    cdsa__cc_id=1008,
    cdsa__representative=UserFactory.create(name="Jerry"),
    cdsa__institution="Lundquist",
    cdsa__representative_role="Analysis Center PI",
    cdsa__type=models.CDSA.DATA_AFFILIATE_COMPONENT,
    component_of=cdsa_1006,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1008.cdsa.anvil_access_group
)

cdsa_1009 = factories.NonDataAffiliateFactory.create(
    cdsa__cc_id=1009,
    cdsa__representative=UserFactory.create(name="ExpertA"),
    cdsa__institution="UABC",
    study_or_center="CenterXYZ",
    cdsa__representative_role="Contact PI",
    cdsa__type=models.CDSA.NON_DATA_AFFILIATE,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_auth_group, child_group=cdsa_1009.cdsa.anvil_access_group
)


# Add some users to the CDSA groups.
accounts = AccountFactory.create_batch(10, verified=True)
GroupAccountMembershipFactory.create(
    group=cdsa_1001.cdsa.anvil_access_group, account=accounts[0]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1001.cdsa.anvil_access_group, account=accounts[1]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1001.cdsa.anvil_access_group, account=accounts[2]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1002.cdsa.anvil_access_group, account=accounts[3]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1002.cdsa.anvil_access_group, account=accounts[4]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1003.cdsa.anvil_access_group, account=accounts[5]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1005.cdsa.anvil_access_group, account=accounts[6]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1005.cdsa.anvil_access_group, account=accounts[7]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1006.cdsa.anvil_access_group, account=accounts[8]
)
GroupAccountMembershipFactory.create(
    group=cdsa_1006.cdsa.anvil_access_group, account=accounts[9]
)

cdsa_workspace_1 = factories.CDSAWorkspaceFactory.create(
    cdsa=cdsa_1006,
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
    data_use_permission=dup,
)
cdsa_workspace_2.workspace.authorization_domains.add(cdsa_auth_group)
cdsa_workspace_2.data_use_modifiers.add(dum)
