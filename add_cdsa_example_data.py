# Temporary script to create some test data.
# Run with: python manage.py shell < add_cdsa_example_data.py

from anvil_consortium_manager.models import ManagedGroup
from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
    WorkspaceGroupSharingFactory,
)

from primed.cdsa.tests import factories
from primed.duo.tests.factories import DataUseModifierFactory, DataUsePermissionFactory
from primed.primed_anvil.models import Study, StudySite
from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
from primed.users.models import User
from primed.users.tests.factories import UserFactory

# Create some agreement versions
v10 = factories.AgreementVersionFactory.create(major_version=1, minor_version=0)
v11 = factories.AgreementVersionFactory.create(major_version=1, minor_version=1)

# Create a couple signed CDSAs.
dup = DataUsePermissionFactory.create(abbreviation="GRU")
dum = DataUseModifierFactory.create(abbreviation="NPU")

# create the CDSA auth group
cdsa_group = ManagedGroupFactory.create(name="PRIMED_CDSA")

# Create some study sites.
StudySiteFactory.create(short_name="CARDINAL", full_name="CARDINAL")
# Create some studies.
StudyFactory.create(short_name="Amish", full_name="Amish")
StudyFactory.create(short_name="MESA", full_name="MESA")

# Create some CDSAs
cdsa_1001 = factories.MemberAgreementFactory.create(
    signed_agreement__cc_id=1001,
    signed_agreement__representative=UserFactory.create(name="Ken Rice"),
    signed_agreement__signing_institution="UW",
    signed_agreement__representative_role="Contact PI",
    signed_agreement__is_primary=True,
    signed_agreement__version=v10,
    study_site=StudySite.objects.get(short_name="CC"),
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_group, child_group=cdsa_1001.signed_agreement.anvil_access_group
)

cdsa_1002 = factories.MemberAgreementFactory.create(
    signed_agreement__cc_id=1002,
    signed_agreement__representative=UserFactory.create(name="Sally Adebamowo"),
    signed_agreement__signing_institution="UM",
    signed_agreement__representative_role="Contact PI",
    signed_agreement__is_primary=True,
    signed_agreement__version=v10,
    study_site=StudySite.objects.get(short_name="CARDINAL"),
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_group, child_group=cdsa_1002.signed_agreement.anvil_access_group
)

cdsa_1003 = factories.MemberAgreementFactory.create(
    signed_agreement__cc_id=1003,
    signed_agreement__representative=UserFactory.create(name="Bamidele Tayo"),
    signed_agreement__signing_institution="Loyola",
    signed_agreement__representative_role="Co-PI",
    signed_agreement__is_primary=False,
    signed_agreement__version=v10,
    study_site=StudySite.objects.get(short_name="CARDINAL"),
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_group, child_group=cdsa_1003.signed_agreement.anvil_access_group
)

cdsa_1004 = factories.MemberAgreementFactory.create(
    signed_agreement__cc_id=1004,
    signed_agreement__representative=UserFactory.create(name="Brackie Mitchell"),
    signed_agreement__signing_institution="UM",
    signed_agreement__representative_role="Co-I",
    signed_agreement__is_primary=False,
    signed_agreement__version=v11,
    study_site=StudySite.objects.get(short_name="CARDINAL"),
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_group, child_group=cdsa_1004.signed_agreement.anvil_access_group
)

cdsa_1005 = factories.DataAffiliateAgreementFactory.create(
    signed_agreement__cc_id=1005,
    signed_agreement__representative=User.objects.get(name="Brackie Mitchell"),
    signed_agreement__signing_institution="UMaryland",
    signed_agreement__representative_role="Study PI",
    study=Study.objects.get(short_name="Amish"),
    signed_agreement__version=v10,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_group, child_group=cdsa_1005.signed_agreement.anvil_access_group
)

cdsa_1006 = factories.DataAffiliateAgreementFactory.create(
    signed_agreement__cc_id=1006,
    signed_agreement__representative=UserFactory.create(name="Robyn"),
    signed_agreement__representative_role="DCC PI",
    signed_agreement__signing_institution="UW",
    study=Study.objects.get(short_name="MESA"),
    signed_agreement__version=v10,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_group, child_group=cdsa_1006.signed_agreement.anvil_access_group
)

cdsa_1007 = factories.DataAffiliateAgreementFactory.create(
    signed_agreement__cc_id=1007,
    signed_agreement__representative=UserFactory.create(name="Wendy"),
    signed_agreement__signing_institution="JHU",
    signed_agreement__representative_role="Field Center PI",
    signed_agreement__is_primary=False,
    study=Study.objects.get(short_name="MESA"),
    signed_agreement__version=v10,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_group, child_group=cdsa_1007.signed_agreement.anvil_access_group
)

cdsa_1008 = factories.DataAffiliateAgreementFactory.create(
    signed_agreement__cc_id=1008,
    signed_agreement__representative=UserFactory.create(name="Jerry"),
    signed_agreement__signing_institution="Lundquist",
    signed_agreement__representative_role="Analysis Center PI",
    signed_agreement__is_primary=False,
    study=Study.objects.get(short_name="MESA"),
    signed_agreement__version=v10,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_group, child_group=cdsa_1008.signed_agreement.anvil_access_group
)

cdsa_1009 = factories.NonDataAffiliateAgreementFactory.create(
    signed_agreement__cc_id=1009,
    signed_agreement__representative=UserFactory.create(name="ExpertA"),
    signed_agreement__signing_institution="UABC",
    affiliation="CenterXYZ",
    signed_agreement__representative_role="Contact PI",
    signed_agreement__version=v10,
)
# DO not add to cdsa group to demonstrate audit
# GroupGroupMembershipFactory.create(
#     parent_group=cdsa_group, child_group=cdsa_1009.signed_agreement.anvil_access_group
# )


# Add some users to the CDSA groups.
accounts = AccountFactory.create_batch(10, verified=True)
GroupAccountMembershipFactory.create(
    group=cdsa_1001.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)
GroupAccountMembershipFactory.create(
    group=cdsa_1001.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)
GroupAccountMembershipFactory.create(
    group=cdsa_1001.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)
GroupAccountMembershipFactory.create(
    group=cdsa_1002.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)
GroupAccountMembershipFactory.create(
    group=cdsa_1002.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)
GroupAccountMembershipFactory.create(
    group=cdsa_1003.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)
GroupAccountMembershipFactory.create(
    group=cdsa_1005.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)
GroupAccountMembershipFactory.create(
    group=cdsa_1005.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)
GroupAccountMembershipFactory.create(
    group=cdsa_1006.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)
GroupAccountMembershipFactory.create(
    group=cdsa_1006.signed_agreement.anvil_access_group,
    account__user=UserFactory.create(),
)

cdsa_workspace_1 = factories.CDSAWorkspaceFactory.create(
    workspace__billing_project__name="demo-primed-cdsa",
    workspace__name="DEMO_PRIMED_CDSA_MESA_1",
    study=Study.objects.get(short_name="MESA"),
    data_use_permission=dup,
)
GroupGroupMembershipFactory.create(
    parent_group=cdsa_workspace_1.workspace.authorization_domains.first(),
    child_group=cdsa_group,
)

# Share with primed_all.
primed_all_group = ManagedGroup.objects.get(name="PRIMED_ALL")
WorkspaceGroupSharingFactory.create(
    group=primed_all_group, workspace=cdsa_workspace_1.workspace
)

# Create a second workspace that is not shared.
cdsa_workspace_2 = factories.CDSAWorkspaceFactory.create(
    workspace__billing_project__name="demo-primed-cdsa",
    workspace__name="DEMO_PRIMED_CDSA_MESA_2",
    study=Study.objects.get(short_name="MESA"),
    data_use_permission=dup,
)
cdsa_workspace_2.workspace.authorization_domains.add(cdsa_group)
cdsa_workspace_2.data_use_modifiers.add(dum)
