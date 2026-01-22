from unittest.mock import patch

import responses
from anvil_consortium_manager.adapters.default import DefaultWorkspaceAdapter
from anvil_consortium_manager.models import Account, GroupAccountMembership, GroupGroupMembership, WorkspaceGroupSharing
from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
    ManagedGroupFactory,
    WorkspaceFactory,
    WorkspaceGroupSharingFactory,
)
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.core import mail
from django.test import TestCase, override_settings

from primed.cdsa.tests.factories import DataAffiliateAgreementFactory, SignedAgreementFactory
from primed.dbgap.tests.factories import dbGaPApplicationFactory
from primed.primed_anvil.tests.factories import StudySiteFactory
from primed.users.tests.factories import UserFactory

from .. import adapters


class AccountAdapterTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the AccountAdapter, where not tested in other TestCases."""

    def test_get_autocomplete_label_linked_user(self):
        """get_autcomplete_label returns correct string when account has a linked user."""
        user = UserFactory.create(name="Test name")
        account = AccountFactory.create(email="foo@bar.com", user=user, verified=True)
        self.assertEqual(
            adapters.AccountAdapter().get_autocomplete_label(account),
            "Test name (foo@bar.com)",
        )

    def test_get_autocomplete_label_no_linked_user(self):
        """get_autcomplete_label returns correct string when account does not have a linked user."""
        account = AccountFactory.create(email="foo@bar.com")
        self.assertEqual(
            adapters.AccountAdapter().get_autocomplete_label(account),
            "--- (foo@bar.com)",
        )

    def test_autocomplete_queryset_matches_user_name(self):
        """get_autocomplete_label returns correct account when user name matches."""
        user_1 = UserFactory.create(name="First Last")
        account_1 = AccountFactory.create(email="test1@test.com", user=user_1, verified=True)
        user_2 = UserFactory.create(name="Foo Bar")
        account_2 = AccountFactory.create(email="test2@test.com", user=user_2, verified=True)
        queryset = adapters.AccountAdapter().get_autocomplete_queryset(Account.objects.all(), "last")
        self.assertEqual(len(queryset), 1)
        self.assertIn(account_1, queryset)
        self.assertNotIn(account_2, queryset)

    def test_autocomplete_queryset_matches_account_email(self):
        """get_autocomplete_label returns correct account when user email matches."""
        user_1 = UserFactory.create(name="First Last")
        account_1 = AccountFactory.create(email="test1@test.com", user=user_1, verified=True)
        user_2 = UserFactory.create(name="Foo Bar")
        account_2 = AccountFactory.create(email="username@domain.com", user=user_2, verified=True)
        queryset = adapters.AccountAdapter().get_autocomplete_queryset(Account.objects.all(), "test")
        self.assertEqual(len(queryset), 1)
        self.assertIn(account_1, queryset)
        self.assertNotIn(account_2, queryset)

    def test_autocomplete_queryset_no_linked_user(self):
        """get_autocomplete_label returns correct account when user name matches."""
        account_1 = AccountFactory.create(email="foo@bar.com")
        account_2 = AccountFactory.create(email="test@test.com")
        queryset = adapters.AccountAdapter().get_autocomplete_queryset(Account.objects.all(), "bar")
        self.assertEqual(len(queryset), 1)
        self.assertIn(account_1, queryset)
        self.assertNotIn(account_2, queryset)

    def test_after_account_verification_no_study_sites(self):
        """A user is not part of any study sites."""
        StudySiteFactory.create()
        account = AccountFactory.create(verified=True)
        adapters.AccountAdapter().after_account_verification(account)
        self.assertEqual(GroupAccountMembership.objects.count(), 0)

    def test_after_account_verification_one_study_site(self):
        """A user is part of one study site."""
        member_group = ManagedGroupFactory.create()
        study_site = StudySiteFactory.create(member_group=member_group)
        user = UserFactory.create()
        user.study_sites.add(study_site)
        account = AccountFactory.create(user=user, verified=True)
        # API response for study site membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership = GroupAccountMembership.objects.first()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_two_study_sites(self):
        """A user is part of two study sites."""
        member_group_1 = ManagedGroupFactory.create()
        study_site_1 = StudySiteFactory.create(member_group=member_group_1)
        member_group_2 = ManagedGroupFactory.create()
        study_site_2 = StudySiteFactory.create(member_group=member_group_2)
        user = UserFactory.create()
        user.study_sites.add(study_site_1)
        user.study_sites.add(study_site_2)
        account = AccountFactory.create(user=user, verified=True)
        # API response for study site membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_1.name}/member/{account.email}",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_2.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 2)
        membership = GroupAccountMembership.objects.get(group=member_group_1, account=account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)
        membership = GroupAccountMembership.objects.get(group=member_group_2, account=account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_already_member(self):
        """The account is already a member of the study site member group."""
        member_group = ManagedGroupFactory.create()
        study_site = StudySiteFactory.create(member_group=member_group)
        user = UserFactory.create()
        user.study_sites.add(study_site)
        account = AccountFactory.create(user=user, verified=True)
        # Add as a member.
        membership = GroupAccountMembershipFactory.create(account=account, group=member_group)
        # No API call expected.
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership.refresh_from_db()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_one_study_site_no_member_groups(self):
        """A user is linked to a study site with no members group."""
        user = UserFactory.create()
        study_site = StudySiteFactory.create(member_group=None)
        user.study_sites.add(study_site)
        account = AccountFactory.create(user=user, verified=True)
        # No mocked API responses
        adapters.AccountAdapter().after_account_verification(account)
        self.assertEqual(GroupAccountMembership.objects.count(), 0)

    def test_after_account_verification_no_dbgap_applications(self):
        """A user is not linked to any dbGaP applications."""
        dbGaPApplicationFactory.create(anvil_access_group=ManagedGroupFactory.create())
        account = AccountFactory.create(verified=True)
        adapters.AccountAdapter().after_account_verification(account)
        self.assertEqual(GroupAccountMembership.objects.count(), 0)

    def test_after_account_verification_pi_one_dbgap_application(self):
        """A user is the PI on one dbGaP application."""
        member_group = ManagedGroupFactory.create()
        user = UserFactory.create()
        dbGaPApplicationFactory.create(principal_investigator=user, anvil_access_group=member_group)
        account = AccountFactory.create(user=user, verified=True)
        # API response for membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership = GroupAccountMembership.objects.first()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_pi_two_dbgap_applications(self):
        """A user is the PI on one dbGaP application."""
        member_group_1 = ManagedGroupFactory.create()
        member_group_2 = ManagedGroupFactory.create()
        user = UserFactory.create()
        dbGaPApplicationFactory.create(principal_investigator=user, anvil_access_group=member_group_1)
        dbGaPApplicationFactory.create(principal_investigator=user, anvil_access_group=member_group_2)
        account = AccountFactory.create(user=user, verified=True)
        # API response for membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_1.name}/member/{account.email}",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_2.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 2)
        membership = GroupAccountMembership.objects.get(account=account, group=member_group_1)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)
        membership = GroupAccountMembership.objects.get(account=account, group=member_group_2)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_pi_already_member(self):
        """The account is already a member of the dbGaP access group."""
        member_group = ManagedGroupFactory.create()
        user = UserFactory.create()
        dbGaPApplicationFactory.create(principal_investigator=user, anvil_access_group=member_group)
        account = AccountFactory.create(user=user, verified=True)
        membership = GroupAccountMembershipFactory.create(account=account, group=member_group)
        # No API call expected.
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership.refresh_from_db()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_collaborator_one_dbgap_application(self):
        """A user is a collaborator on one dbGaP application"""
        member_group = ManagedGroupFactory.create()
        user = UserFactory.create()
        app = dbGaPApplicationFactory.create(anvil_access_group=member_group)
        app.collaborators.add(user)
        account = AccountFactory.create(user=user, verified=True)
        # API response for membership
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership = GroupAccountMembership.objects.first()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_collaborator_two_dbgap_applications(self):
        """A user is a collaborator on one dbGaP application"""
        member_group_1 = ManagedGroupFactory.create()
        member_group_2 = ManagedGroupFactory.create()
        user = UserFactory.create()
        app_1 = dbGaPApplicationFactory.create(anvil_access_group=member_group_1)
        app_1.collaborators.add(user)
        app_2 = dbGaPApplicationFactory.create(anvil_access_group=member_group_2)
        app_2.collaborators.add(user)
        account = AccountFactory.create(user=user, verified=True)
        # API response for membership
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_1.name}/member/{account.email}",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_2.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 2)
        membership = GroupAccountMembership.objects.first()
        membership = GroupAccountMembership.objects.get(account=account, group=member_group_1)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)
        membership = GroupAccountMembership.objects.get(account=account, group=member_group_2)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_collaborator_already_member(self):
        """The account is already a member of the access group."""
        member_group = ManagedGroupFactory.create()
        user = UserFactory.create()
        app = dbGaPApplicationFactory.create(anvil_access_group=member_group)
        app.collaborators.add(user)
        account = AccountFactory.create(user=user, verified=True)
        membership = GroupAccountMembershipFactory.create(account=account, group=member_group)
        # No API call expected.
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership.refresh_from_db()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_pi_and_collaborator_one_dbgap_application(self):
        """A User is both PI and collaborator on one dbGaP application."""
        member_group = ManagedGroupFactory.create()
        user = UserFactory.create()
        app = dbGaPApplicationFactory.create(principal_investigator=user, anvil_access_group=member_group)
        app.collaborators.add(user)
        account = AccountFactory.create(user=user, verified=True)
        # API response for membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership = GroupAccountMembership.objects.get(group=member_group, account=account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_pi_and_collaborator_two_dbgap_application(self):
        """A User is both PI on one dbGaP application and a collaborator on another."""
        member_group_1 = ManagedGroupFactory.create()
        member_group_2 = ManagedGroupFactory.create()
        user = UserFactory.create()
        dbGaPApplicationFactory.create(principal_investigator=user, anvil_access_group=member_group_1)
        app_2 = dbGaPApplicationFactory.create(anvil_access_group=member_group_2)
        app_2.collaborators.add(user)
        account = AccountFactory.create(user=user, verified=True)
        # API response for membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_1.name}/member/{account.email}",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_2.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 2)
        membership = GroupAccountMembership.objects.get(group=member_group_1, account=account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)
        membership = GroupAccountMembership.objects.get(group=member_group_2, account=account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_no_signed_agreements(self):
        """A user is not associated with any signed agreements."""
        SignedAgreementFactory.create(anvil_access_group=ManagedGroupFactory.create())
        account = AccountFactory.create(verified=True)
        adapters.AccountAdapter().after_account_verification(account)
        self.assertEqual(GroupAccountMembership.objects.count(), 0)

    def test_after_account_verification_one_signed_agreement(self):
        """A user is an accessor on one CDSA signed agreement."""
        member_group = ManagedGroupFactory.create()
        user = UserFactory.create()
        sa = SignedAgreementFactory.create(anvil_access_group=member_group)
        sa.accessors.add(user)
        account = AccountFactory.create(user=user, verified=True)
        # API response for membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership = GroupAccountMembership.objects.first()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_two_signed_agreements(self):
        """A user is an accessor on two signed agreements."""
        member_group_1 = ManagedGroupFactory.create()
        member_group_2 = ManagedGroupFactory.create()
        user = UserFactory.create()
        sa1 = SignedAgreementFactory.create(anvil_access_group=member_group_1)
        sa1.accessors.add(user)
        sa2 = SignedAgreementFactory.create(anvil_access_group=member_group_2)
        sa2.accessors.add(user)
        account = AccountFactory.create(user=user, verified=True)
        # API response for membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_1.name}/member/{account.email}",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_2.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 2)
        membership = GroupAccountMembership.objects.get(group=member_group_1, account=account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)
        membership = GroupAccountMembership.objects.get(group=member_group_2, account=account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_one_signed_agreement_alraedy_member(self):
        """A user is already a member of the access group."""
        member_group = ManagedGroupFactory.create()
        user = UserFactory.create()
        sa = SignedAgreementFactory.create(anvil_access_group=member_group)
        sa.accessors.add(user)
        account = AccountFactory.create(user=user, verified=True)
        membership = GroupAccountMembershipFactory.create(group=member_group, account=account)
        # No API call expected.
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership.refresh_from_db()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_no_data_affiliate_agreements(self):
        """A user is not an uploader on any signed data affiliate CDSAs"""
        DataAffiliateAgreementFactory.create(anvil_upload_group=ManagedGroupFactory.create())
        account = AccountFactory.create(verified=True)
        adapters.AccountAdapter().after_account_verification(account)
        self.assertEqual(GroupAccountMembership.objects.count(), 0)

    def test_after_account_verification_one_data_affiliate_agreements(self):
        """A user is an uploader on one signed data affiliate CDSA"""
        member_group = ManagedGroupFactory.create()
        user = UserFactory.create()
        daa = DataAffiliateAgreementFactory.create(anvil_upload_group=member_group)
        daa.uploaders.add(user)
        account = AccountFactory.create(user=user, verified=True)
        print(type(account))
        # API response for membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership = GroupAccountMembership.objects.first()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_two_data_affiliate_agreements(self):
        """A user is an uploader on two signed data affiliate CDSA"""
        member_group_1 = ManagedGroupFactory.create()
        member_group_2 = ManagedGroupFactory.create()
        user = UserFactory.create()
        daa_1 = DataAffiliateAgreementFactory.create(anvil_upload_group=member_group_1)
        daa_1.uploaders.add(user)
        daa_2 = DataAffiliateAgreementFactory.create(anvil_upload_group=member_group_2)
        daa_2.uploaders.add(user)
        account = AccountFactory.create(user=user, verified=True)
        # API response for membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_1.name}/member/{account.email}",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + f"/api/groups/v1/{member_group_2.name}/member/{account.email}",
            status=204,
        )
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 2)
        membership = GroupAccountMembership.objects.get(group=member_group_1, account=account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)
        membership = GroupAccountMembership.objects.get(group=member_group_2, account=account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_after_account_verification_one_data_affiliate_agreement_already_member(self):
        """The account is already a member of the CDSA uploader group."""
        member_group = ManagedGroupFactory.create()
        user = UserFactory.create()
        daa = DataAffiliateAgreementFactory.create(anvil_upload_group=member_group)
        daa.uploaders.add(user)
        account = AccountFactory.create(user=user, verified=True)
        membership = GroupAccountMembershipFactory.create(account=account, group=member_group)
        # No API call expected.
        adapters.AccountAdapter().after_account_verification(account)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupAccountMembership.objects.count(), 1)
        membership.refresh_from_db()
        self.assertEqual(membership.group, member_group)
        self.assertEqual(membership.account, account)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.MEMBER)

    def test_get_account_verification_notification_context(self):
        account = AccountFactory.create(verified=True)
        context = adapters.AccountAdapter().get_account_verification_notification_context(account)
        self.assertEqual(context["email"], account.email)
        self.assertEqual(context["user"], account.user)
        self.assertIn("memberships", context)
        self.assertEqual(len(context["memberships"]), 0)
        # One membership
        membership_1 = GroupAccountMembershipFactory.create(account=account)
        context = adapters.AccountAdapter().get_account_verification_notification_context(account)
        self.assertEqual(len(context["memberships"]), 1)
        self.assertIn(membership_1, context["memberships"])
        # Two memberships
        membership_2 = GroupAccountMembershipFactory.create(account=account)
        context = adapters.AccountAdapter().get_account_verification_notification_context(account)
        self.assertEqual(len(context["memberships"]), 2)
        self.assertIn(membership_1, context["memberships"])
        self.assertIn(membership_2, context["memberships"])

    def test_send_account_verification_notification_email_includes_memberships(self):
        """The account verification notification email includes a list of the account memberships."""
        account = AccountFactory.create(verified=True)
        membership = GroupAccountMembershipFactory.create(account=account)
        with self.assertTemplateUsed("primed_anvil/account_notification_email.html"):
            adapters.AccountAdapter().send_account_verification_notification_email(account)
        # Check that the email was sent.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        # Check that the email contains the account email.
        self.assertIn(account.email, email.body)
        # Check that the email contains the username
        self.assertIn(account.user.username, email.body)
        # Check that the email contains the membership info.
        self.assertIn(str(membership), email.body)


class WorkspaceAuthDomainAdapterMixinTest(AnVILAPIMockTestMixin, TestCase):
    def setUp(self):
        super().setUp()

        class TestAdapter(adapters.WorkspaceAuthDomainAdapterMixin, DefaultWorkspaceAdapter):
            pass

        self.adapter = TestAdapter()

    def test_before_anvil_create(self):
        admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        workspace = WorkspaceFactory.create(name="foo", workspace_type=self.adapter.get_type())
        # API response for auth domain ManagedGroup creation.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo",
            status=201,
        )
        # API response for auth domain PRIMED_ADMINS membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        # Run the adapter method.
        self.adapter.before_anvil_create(workspace)
        self.assertEqual(workspace.authorization_domains.count(), 1)
        auth_domain = workspace.authorization_domains.get()
        self.assertEqual(auth_domain.name, "AUTH_foo")
        self.assertTrue(auth_domain.is_managed_by_app)
        self.assertEqual(auth_domain.email, "AUTH_foo@firecloud.org")
        # Check for GroupGroupMembership.
        self.assertEqual(GroupGroupMembership.objects.count(), 1)
        membership = GroupGroupMembership.objects.first()
        self.assertEqual(membership.parent_group, auth_domain)
        self.assertEqual(membership.child_group, admins_group)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foobar")
    def test_before_anvil_create_different_cc_admins_name(self):
        admins_group = ManagedGroupFactory.create(name="foobar")
        # Create a Workspace instead of CDSAWorkspace to skip factory auth domain behavior.
        workspace = WorkspaceFactory.create(name="foo", workspace_type=self.adapter.get_type())
        # API response for auth domain ManagedGroup creation.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo",
            status=201,
        )
        # API response for auth domain PRIMED_ADMINS membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo/admin/foobar@firecloud.org",
            status=204,
        )
        # Run the adapter method.
        self.adapter.before_anvil_create(workspace)
        self.assertEqual(workspace.authorization_domains.count(), 1)
        auth_domain = workspace.authorization_domains.get()
        self.assertEqual(auth_domain.name, "AUTH_foo")
        self.assertTrue(auth_domain.is_managed_by_app)
        self.assertEqual(auth_domain.email, "AUTH_foo@firecloud.org")
        # Check for GroupGroupMembership.
        self.assertEqual(GroupGroupMembership.objects.count(), 1)
        membership = GroupGroupMembership.objects.first()
        self.assertEqual(membership.parent_group, auth_domain)
        self.assertEqual(membership.child_group, admins_group)

    def test_before_anvil_create_admins_group_does_not_exist(self):
        """If the admins group does not exist, the workspace is not shared."""
        workspace = WorkspaceFactory.create(name="foo", workspace_type=self.adapter.get_type())
        # API response for auth domain ManagedGroup creation.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo",
            status=201,
        )
        # Run the adapter method.
        self.adapter.before_anvil_create(workspace)
        self.assertEqual(workspace.authorization_domains.count(), 1)
        auth_domain = workspace.authorization_domains.get()
        self.assertEqual(auth_domain.name, "AUTH_foo")
        self.assertTrue(auth_domain.is_managed_by_app)
        self.assertEqual(auth_domain.email, "AUTH_foo@firecloud.org")
        # No GroupGroupMembership objects were created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)


class WorkspaceSharingAdapterMixinTest(AnVILAPIMockTestMixin, TestCase):
    def setUp(self):
        super().setUp()

        class TestAdapter(adapters.WorkspaceSharingAdapterMixin, DefaultWorkspaceAdapter):
            share_permissions = [
                adapters.PrimedWorkspacePermissions.PRIMED_CC_WRITER,
                adapters.PrimedWorkspacePermissions.PRIMED_CC_ADMIN,
            ]

        class TestSingleShareAdapter(adapters.WorkspaceSharingAdapterMixin, DefaultWorkspaceAdapter):
            share_permissions = [
                adapters.PrimedWorkspacePermissions.PRIMED_CC_WRITER,
            ]

        self.adapter = TestAdapter()
        self.single_share_adapter = TestSingleShareAdapter()

    def test_no_share_permissions_set(self):
        class BadTestAdapter(adapters.WorkspaceSharingAdapterMixin, DefaultWorkspaceAdapter):
            pass

        bad_adapter = BadTestAdapter()
        with self.assertRaises(NotImplementedError):
            bad_adapter.get_share_permissions()

    def test_empty_list_share_permissions(self):
        class BadTestAdapter(adapters.WorkspaceSharingAdapterMixin, DefaultWorkspaceAdapter):
            share_permissions = []

        bad_adapter = BadTestAdapter()
        with self.assertRaises(ValueError):
            bad_adapter.get_share_permissions()

    def test_after_anvil_create(self):
        for perm_set in self.adapter.get_share_permissions():
            share_group_name = perm_set.group_name
            share_permission = perm_set.access

            ManagedGroupFactory.create(name=share_group_name)

            workspace = WorkspaceFactory.create(
                billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
            )
            # API response for workspace owner.
            acls = [
                {
                    "email": f"{share_group_name}@firecloud.org",
                    "accessLevel": share_permission,
                    "canShare": False,
                    "canCompute": True,
                }
            ]
            self.anvil_response_mock.add(
                responses.PATCH,
                self.api_client.rawls_entry_point + "/api/workspaces/bar/foo/acl?inviteUsersNotFound=false",
                status=200,
                match=[responses.matchers.json_params_matcher(acls)],
                json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
            )
        # Run the adapter method.
        self.adapter.after_anvil_create(workspace)

        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), len(self.adapter.share_permissions))

        for perm_set in self.adapter.get_share_permissions():
            share_group_name = perm_set.group_name
            share_permission = perm_set.access
            share_can_compute = perm_set.can_compute
            sharing = WorkspaceGroupSharing.objects.get(workspace=workspace, group__name=share_group_name)
            self.assertEqual(sharing.access, share_permission)
            self.assertEqual(sharing.can_compute, share_can_compute)

    def test_after_anvil_create_different_admins_group(self):
        share_group_name = "foobar"
        share_permission = WorkspaceGroupSharing.WRITER
        alt_share_permissions = [
            adapters.WorkspaceSharingPermission(group_name=share_group_name, access=share_permission, can_compute=True)
        ]
        with patch.object(self.adapter, "share_permissions", alt_share_permissions):
            share_group = ManagedGroupFactory.create(name=share_group_name)
            workspace = WorkspaceFactory.create(
                billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
            )
            # API response for workspace owner.
            acls = [
                {
                    "email": f"{share_group_name}@firecloud.org",
                    "accessLevel": share_permission,
                    "canShare": False,
                    "canCompute": True,
                }
            ]
            self.anvil_response_mock.add(
                responses.PATCH,
                self.api_client.rawls_entry_point + "/api/workspaces/bar/foo/acl?inviteUsersNotFound=false",
                status=200,
                match=[responses.matchers.json_params_matcher(acls)],
                json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
            )
            # Run the adapter method.
            self.adapter.after_anvil_create(workspace)
            # Check for WorkspaceGroupSharing.
            self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
            sharing = WorkspaceGroupSharing.objects.first()
            self.assertEqual(sharing.workspace, workspace)
            self.assertEqual(sharing.group, share_group)
            self.assertEqual(sharing.access, share_permission)
            self.assertTrue(sharing.can_compute)

    def test_after_anvil_create_no_admins_group(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
        )
        # Run the adapter method.
        self.adapter.after_anvil_create(workspace)
        # No WorkspaceGroupSharing objects were created.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 0)

    def test_after_anvil_import(self):
        for perm_set in self.adapter.get_share_permissions():
            share_group_name = perm_set.group_name
            share_permission = perm_set.access
            ManagedGroupFactory.create(name=share_group_name)
            workspace = WorkspaceFactory.create(
                billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
            )
            # API response for admin group workspace owner.
            acls = [
                {
                    "email": f"{share_group_name}@firecloud.org",
                    "accessLevel": share_permission,
                    "canShare": False,
                    "canCompute": True,
                }
            ]
            self.anvil_response_mock.add(
                responses.PATCH,
                self.api_client.rawls_entry_point + "/api/workspaces/bar/foo/acl?inviteUsersNotFound=false",
                status=200,
                match=[responses.matchers.json_params_matcher(acls)],
                json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
            )
        # Run the adapter method.
        self.adapter.after_anvil_import(workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), len(self.adapter.share_permissions))
        for perm_set in self.adapter.get_share_permissions():
            share_group_name = perm_set.group_name
            share_permission = perm_set.access
            share_can_compute = perm_set.can_compute
            sharing = WorkspaceGroupSharing.objects.get(workspace=workspace, group__name=share_group_name)
            self.assertEqual(sharing.access, share_permission)
            self.assertEqual(sharing.can_compute, share_can_compute)

    def test_after_anvil_import_different_admins_group(self):
        alt_perms = [
            adapters.WorkspaceSharingPermission(
                group_name="foobar", access=WorkspaceGroupSharing.WRITER, can_compute=True
            )
        ]
        with patch.object(self.adapter, "share_permissions", alt_perms):
            share_permission = self.adapter.share_permissions[0].access
            admins_group = ManagedGroupFactory.create(name="foobar")
            workspace = WorkspaceFactory.create(
                billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
            )
            # API response for admin group workspace owner.
            acls = [
                {
                    "email": "foobar@firecloud.org",
                    "accessLevel": share_permission,
                    "canShare": False,
                    "canCompute": True,
                }
            ]
            self.anvil_response_mock.add(
                responses.PATCH,
                self.api_client.rawls_entry_point + "/api/workspaces/bar/foo/acl?inviteUsersNotFound=false",
                status=200,
                match=[responses.matchers.json_params_matcher(acls)],
                json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
            )
            # Run the adapter method.
            self.adapter.after_anvil_import(workspace)
            # Check for WorkspaceGroupSharing.
            self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
            sharing = WorkspaceGroupSharing.objects.first()
            self.assertEqual(sharing.workspace, workspace)
            self.assertEqual(sharing.group, admins_group)
            self.assertEqual(sharing.access, share_permission)
            self.assertTrue(sharing.can_compute)

    def test_after_anvil_import_no_admins_group(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
        )
        # Run the adapter method.
        self.adapter.after_anvil_import(workspace)
        # No WorkspaceGroupSharing objects were created.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 0)

    def test_after_anvil_import_already_shared(self):
        with patch.object(self, "adapter", self.single_share_adapter):
            share_group = self.adapter.share_permissions[0].group_name
            share_permission = self.adapter.share_permissions[0].access
            share_can_compute = self.adapter.share_permissions[0].can_compute
            admins_group = ManagedGroupFactory.create(name=share_group)
            workspace = WorkspaceFactory.create(workspace_type=self.adapter.get_type())
            WorkspaceGroupSharingFactory.create(
                workspace=workspace,
                group=admins_group,
                access=share_permission,
                can_compute=True,
            )
            # No API call - record already exists.
            # Run the adapter method.
            self.adapter.after_anvil_import(workspace)
            # Check for WorkspaceGroupSharing.
            self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
            sharing = WorkspaceGroupSharing.objects.first()
            self.assertEqual(sharing.workspace, workspace)
            self.assertEqual(sharing.group, admins_group)
            self.assertEqual(sharing.access, share_permission)
            self.assertEqual(sharing.can_compute, share_can_compute)

    def test_after_anvil_import_already_shared_wrong_access(self):
        with patch.object(self, "adapter", self.single_share_adapter):
            share_group = self.adapter.share_permissions[0].group_name
            share_permission = self.adapter.share_permissions[0].access
            share_can_compute = self.adapter.share_permissions[0].can_compute
            admins_group = ManagedGroupFactory.create(name=share_group)
            workspace = WorkspaceFactory.create(
                billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
            )
            sharing = WorkspaceGroupSharingFactory.create(
                workspace=workspace,
                group=admins_group,
                access=WorkspaceGroupSharing.READER,
                can_compute=True,
            )
            # API response to update sharing.
            acls = [
                {
                    "email": f"{share_group}@firecloud.org",
                    "accessLevel": share_permission,
                    "canShare": False,
                    "canCompute": True,
                }
            ]
            self.anvil_response_mock.add(
                responses.PATCH,
                self.api_client.rawls_entry_point + "/api/workspaces/bar/foo/acl?inviteUsersNotFound=false",
                status=200,
                match=[responses.matchers.json_params_matcher(acls)],
                json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
            )
            # Run the adapter method.
            self.adapter.after_anvil_import(workspace)
            # Check for WorkspaceGroupSharing.
            self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
            sharing.refresh_from_db()
            self.assertEqual(sharing.workspace, workspace)
            self.assertEqual(sharing.group, admins_group)
            self.assertEqual(sharing.access, share_permission)
            self.assertEqual(sharing.can_compute, share_can_compute)

    def test_after_anvil_import_already_shared_wrong_can_compute(self):
        with patch.object(self, "adapter", self.single_share_adapter):
            share_group = self.adapter.share_permissions[0].group_name
            share_permission = self.adapter.share_permissions[0].access
            share_can_compute = self.adapter.share_permissions[0].can_compute
            admins_group = ManagedGroupFactory.create(name=share_group)
            workspace = WorkspaceFactory.create(
                billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
            )
            sharing = WorkspaceGroupSharingFactory.create(
                workspace=workspace,
                group=admins_group,
                access=share_permission,
                can_compute=False,
            )
            # API response to update sharing.
            acls = [
                {
                    "email": f"{share_group}@firecloud.org",
                    "accessLevel": share_permission,
                    "canShare": False,
                    "canCompute": True,
                }
            ]
            self.anvil_response_mock.add(
                responses.PATCH,
                self.api_client.rawls_entry_point + "/api/workspaces/bar/foo/acl?inviteUsersNotFound=false",
                status=200,
                match=[responses.matchers.json_params_matcher(acls)],
                json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
            )
            # Run the adapter method.
            self.adapter.after_anvil_import(workspace)
            # Check for WorkspaceGroupSharing.
            self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
            sharing.refresh_from_db()
            self.assertEqual(sharing.workspace, workspace)
            self.assertEqual(sharing.group, admins_group)
            self.assertEqual(sharing.access, share_permission)
            self.assertEqual(sharing.can_compute, share_can_compute)


class ManagedGroupAdapterTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for the custom PRIMED ManagedGroupAdapter."""

    def setUp(self):
        super().setUp()
        self.adapter = adapters.ManagedGroupAdapter()

    def test_after_anvil_create(self):
        admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        managed_group = ManagedGroupFactory.create(name="test-group")
        # API response for PRIMED_ADMINS membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + "/api/groups/v1/test-group/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        # Run the adapter method.
        self.adapter.after_anvil_create(managed_group)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupGroupMembership.objects.count(), 1)
        membership = GroupGroupMembership.objects.first()
        self.assertEqual(membership.parent_group, managed_group)
        self.assertEqual(membership.child_group, admins_group)
        self.assertEqual(membership.role, GroupGroupMembership.RoleChoices.ADMIN)

    def test_after_anvil_create_no_admins_group(self):
        managed_group = ManagedGroupFactory.create(name="test-group")
        # Run the adapter method.
        self.adapter.after_anvil_create(managed_group)
        # No WorkspaceGroupSharing objects were created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)
