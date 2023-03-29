# Temporary script to create some test data.
# Run with: python manage.py shell < add_cdsa_test_data.py

from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
    ManagedGroupFactory,
)

from primed.cdsa import models
from primed.cdsa.tests import factories

# Create a couple signed CDSAs.

# Member CDSAs
cdsa_member_1 = factories.CDSAFactory.create(type=models.CDSA.MEMBER)
cdsa_member_1_component_1 = factories.CDSAFactory.create(
    type=models.CDSA.MEMBER, is_component=True, group=cdsa_member_1.group
)
cdsa_member_2 = factories.CDSAFactory.create(type=models.CDSA.MEMBER)

# Data affiliate CDSAs
cdsa_da_1 = factories.CDSAFactory.create(type=models.CDSA.DATA_AFFILIATE)
cdsa_da_2 = factories.CDSAFactory.create(type=models.CDSA.DATA_AFFILIATE)
cdsa_da_2_component_1 = factories.CDSAFactory.create(
    type=models.CDSA.DATA_AFFILIATE, is_component=True, group=cdsa_da_2.group
)

# Add some users to the CDSA groups.
accounts = AccountFactory.create_batch(10, verified=True)
GroupAccountMembershipFactory.create(
    group=cdsa_member_1.anvil_access_group, account=accounts[0]
)
GroupAccountMembershipFactory.create(
    group=cdsa_member_1_component_1.anvil_access_group, account=accounts[1]
)
GroupAccountMembershipFactory.create(
    group=cdsa_member_1_component_1.anvil_access_group, account=accounts[2]
)
GroupAccountMembershipFactory.create(
    group=cdsa_member_2.anvil_access_group, account=accounts[3]
)
GroupAccountMembershipFactory.create(
    group=cdsa_da_1.anvil_access_group, account=accounts[4:6]
)
GroupAccountMembershipFactory.create(
    group=cdsa_da_1.anvil_access_group, account=accounts[5]
)
GroupAccountMembershipFactory.create(
    group=cdsa_da_1.anvil_access_group, account=accounts[6]
)
GroupAccountMembershipFactory.create(
    group=cdsa_da_2.anvil_access_group, account=accounts[7]
)
GroupAccountMembershipFactory.create(
    group=cdsa_da_2_component_1.anvil_access_group, account=accounts[8]
)
GroupAccountMembershipFactory.create(
    group=cdsa_da_2_component_1.anvil_access_group, account=accounts[9]
)

# create the CDSA auth group
auth_group = ManagedGroupFactory.create(name="AUTH_PRIMED_CDSA")

cdsa_workspace = factories.CDSAWorkspaceFactory.create(
    cdsa=cdsa_da_1,
    study__full_name=cdsa_da_1.group,
)
cdsa_workspace.workspace.authorization_domains.add(auth_group)
