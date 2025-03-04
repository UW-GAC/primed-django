"""Tests for management commands in the `cdsa` app."""

import os
import tempfile
from io import StringIO
from os.path import isdir, isfile

from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
)
from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from primed.users.tests.factories import UserFactory

from ..tests import factories


class CDSARecordsTest(TestCase):
    """Tests for the records_report command."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.outdir = os.path.join(self.tmpdir.name, "test_output")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_output(self):
        out = StringIO()
        call_command("cdsa_records", "--outdir", self.outdir, "--no-color", stdout=out)
        self.assertIn("generating reports... done!", out.getvalue())

    def test_files_created(self):
        out = StringIO()
        call_command("cdsa_records", "--outdir", self.outdir, "--no-color", stdout=out)
        self.assertTrue(isdir(self.outdir))
        self.assertTrue(isfile(os.path.join(self.outdir, "representative_records.tsv")))
        self.assertTrue(isfile(os.path.join(self.outdir, "study_records.tsv")))
        self.assertTrue(isfile(os.path.join(self.outdir, "workspace_records.tsv")))
        self.assertTrue(isfile(os.path.join(self.outdir, "useraccess_records.tsv")))

    def test_representative_records_zero(self):
        out = StringIO()
        call_command("cdsa_records", "--outdir", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "representative_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

    def test_representative_records_three(self):
        factories.DataAffiliateAgreementFactory.create()
        factories.DataAffiliateAgreementFactory.create()
        factories.NonDataAffiliateAgreementFactory.create()
        out = StringIO()
        call_command("cdsa_records", "--outdir", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "representative_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 4)

    def test_study_records_zero(self):
        out = StringIO()
        call_command("cdsa_records", "--outdir", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "study_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

    def test_study_records_one(self):
        factories.DataAffiliateAgreementFactory.create(is_primary=True)
        out = StringIO()
        call_command("cdsa_records", "--outdir", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "study_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)

    def test_cdsa_workspace_records_zero(self):
        out = StringIO()
        call_command("cdsa_records", "--outdir", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "workspace_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

    def test_cdsa_workspace_records_one(self):
        agreement = factories.DataAffiliateAgreementFactory.create()
        factories.CDSAWorkspaceFactory.create(study=agreement.study)
        out = StringIO()
        call_command("cdsa_records", "--outdir", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "workspace_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)

    def test_directory_exists(self):
        os.mkdir(self.outdir)
        out = StringIO()
        with self.assertRaises(CommandError) as e:
            call_command("cdsa_records", "--outdir", self.outdir, "--no-color", stdout=out)
        self.assertIn("already exists", str(e.exception))


class RunCDSAAuditTest(TestCase):
    """Tests for the run_cdsa_audit command"""

    def setUp(self):
        super().setUp()
        self.cdsa_group = ManagedGroupFactory.create(name=settings.ANVIL_CDSA_GROUP_NAME)

    def test_command_output_no_records(self):
        """Test command output."""
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running SignedAgreement access audit... ok!\n* Verified: 0\n* Needs action: 0\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        expected_output = "Running CDSAWorkspace access audit... ok!\n* Verified: 0\n* Needs action: 0\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(expected_output, out.getvalue())
        expected_output = "Running Accessor audit... ok!\n* Verified: 0\n* Needs action: 0\n* Errors: 0\n"
        expected_output = "Running Uploader audit... ok!\n* Verified: 0\n* Needs action: 0\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(expected_output, out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_agreements_one_agreement_verified(self):
        """Test command output with one verified instance."""
        factories.DataAffiliateAgreementFactory.create(is_primary=False)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running SignedAgreement access audit... ok!\n* Verified: 1\n* Needs action: 0\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_agreements_one_agreement_needs_action(self):
        """Test command output with one needs_action instance."""
        factories.DataAffiliateAgreementFactory.create()
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = (
            "Running SignedAgreement access audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        )
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:signed_agreements:sag:all"), out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_agreements_one_agreement_error(self):
        """Test command output with one error instance."""
        agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False)
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=agreement.signed_agreement.anvil_access_group,
        )
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = (
            "Running SignedAgreement access audit... problems found.\n* Verified: 0\n* Needs action: 0\n* Errors: 1\n"
        )
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:signed_agreements:sag:all"), out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_agreements_one_agreement_verified_email(self):
        """No email is sent when there are no errors."""
        factories.DataAffiliateAgreementFactory.create(is_primary=False)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        self.assertIn("Running SignedAgreement access audit... ok!", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_agreements_one_agreement_needs_action_email(self):
        """Email is sent for one needs_action instance."""
        factories.DataAffiliateAgreementFactory.create()
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        expected_output = (
            "Running SignedAgreement access audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        )
        self.assertIn(expected_output, out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA SignedAgreementAccessAudit errors")
        self.assertIn(reverse("cdsa:audit:signed_agreements:sag:all"), email.alternatives[0][0])

    def test_command_agreements_one_agreement_error_email(self):
        """Test command output with one error instance."""
        agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False)
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=agreement.signed_agreement.anvil_access_group,
        )
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        expected_output = (
            "Running SignedAgreement access audit... problems found.\n* Verified: 0\n* Needs action: 0\n* Errors: 1\n"
        )
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:signed_agreements:sag:all"), out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA SignedAgreementAccessAudit errors")
        self.assertIn(reverse("cdsa:audit:signed_agreements:sag:all"), email.alternatives[0][0])

    def test_command_workspaces_one_workspace_verified(self):
        """Test command output with one verified instance."""
        factories.CDSAWorkspaceFactory.create()
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running CDSAWorkspace access audit... ok!\n* Verified: 1\n* Needs action: 0\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_workspaces_one_workspace_needs_action(self):
        """Test command output with one needs_action instance."""
        agreement = factories.DataAffiliateAgreementFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=agreement.signed_agreement.anvil_access_group,
        )
        factories.CDSAWorkspaceFactory.create(study=agreement.study)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = (
            "Running CDSAWorkspace access audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        )
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:workspaces:all"), out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_workspaces_one_workspace_error(self):
        """Test command output with one error instance."""
        workspace = factories.CDSAWorkspaceFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = (
            "Running CDSAWorkspace access audit... problems found.\n* Verified: 0\n* Needs action: 0\n* Errors: 1\n"
        )
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:workspaces:all"), out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_workspaces_one_workspace_verified_email(self):
        """No email is sent when there are no errors."""
        factories.CDSAWorkspaceFactory.create()
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        self.assertIn("Running CDSAWorkspace access audit... ok!", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_workspaces_one_workspace_needs_action_email(self):
        """Email is sent for one needs_action instance."""
        agreement = factories.DataAffiliateAgreementFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=agreement.signed_agreement.anvil_access_group,
        )
        factories.CDSAWorkspaceFactory.create(study=agreement.study)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        expected_output = (
            "Running CDSAWorkspace access audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        )
        self.assertIn(expected_output, out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA WorkspaceAccessAudit errors")
        self.assertIn(reverse("cdsa:audit:workspaces:all"), email.alternatives[0][0])

    def test_command_workspaces_one_workspace_error_email(self):
        """Test command output with one error instance."""
        workspace = factories.CDSAWorkspaceFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        expected_output = (
            "Running CDSAWorkspace access audit... problems found.\n* Verified: 0\n* Needs action: 0\n* Errors: 1\n"
        )
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:workspaces:all"), out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA WorkspaceAccessAudit errors")
        self.assertIn(reverse("cdsa:audit:workspaces:all"), email.alternatives[0][0])

    def test_accessors_no_accessors(self):
        """Test command output with no accessors."""
        factories.DataAffiliateAgreementFactory.create(is_primary=False)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running Accessor audit... ok!\n* Verified: 0\n* Needs action: 0\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(expected_output, out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_accessors_verified(self):
        """Test command output with one verified instance."""
        agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False)
        agreement.signed_agreement.accessors.add(UserFactory.create())
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running Accessor audit... ok!\n* Verified: 1\n* Needs action: 0\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_accessors_needs_action(self):
        """Test command output with one needs_action instance."""
        agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create(verified=True)
        agreement.signed_agreement.accessors.add(account.user)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running Accessor audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:signed_agreements:accessors:all"), out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_accessors_error(self):
        """Test command output with one error instance."""
        agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False)
        GroupGroupMembershipFactory.create(
            parent_group=agreement.signed_agreement.anvil_access_group,
        )
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running Accessor audit... problems found.\n* Verified: 0\n* Needs action: 0\n* Errors: 1\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:signed_agreements:accessors:all"), out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_accessors_verified_email(self):
        """No email is sent when there are no errors."""
        factories.DataAffiliateAgreementFactory.create(is_primary=False)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        self.assertIn("Running Accessor audit... ok!", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_accessors_needs_action_email(self):
        """Email is sent for one needs_action instance."""
        agreement = factories.DataAffiliateAgreementFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=agreement.signed_agreement.anvil_access_group,
        )
        account = AccountFactory.create(verified=True)
        agreement.signed_agreement.accessors.add(account.user)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        expected_output = "Running Accessor audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA AccessorAudit errors")
        self.assertIn(reverse("cdsa:audit:signed_agreements:accessors:all"), email.alternatives[0][0])

    def test_command_accessors_error_email(self):
        """Test command output with one error instance."""
        agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False)
        GroupGroupMembershipFactory.create(
            parent_group=agreement.signed_agreement.anvil_access_group,
        )
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        expected_output = "Running Accessor audit... problems found.\n* Verified: 0\n* Needs action: 0\n* Errors: 1\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:signed_agreements:accessors:all"), out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA AccessorAudit errors")
        self.assertIn(reverse("cdsa:audit:signed_agreements:accessors:all"), email.alternatives[0][0])

    def test_uploaders_no_uploaders(self):
        """Test command output with no uploaders."""
        factories.DataAffiliateAgreementFactory.create(is_primary=False)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running Uploader audit... ok!\n* Verified: 0\n* Needs action: 0\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(expected_output, out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_uploaders_verified(self):
        """Test command output with one verified instance."""
        agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False)
        agreement.uploaders.add(UserFactory.create())
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running Uploader audit... ok!\n* Verified: 1\n* Needs action: 0\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_uploaders_needs_action(self):
        """Test command output with one needs_action instance."""
        agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create(verified=True)
        agreement.uploaders.add(account.user)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running Uploader audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:signed_agreements:uploaders:all"), out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_uploaders_error(self):
        """Test command output with one error instance."""
        agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False)
        GroupGroupMembershipFactory.create(
            parent_group=agreement.anvil_upload_group,
        )
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = "Running Uploader audit... problems found.\n* Verified: 0\n* Needs action: 0\n* Errors: 1\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:signed_agreements:uploaders:all"), out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_uploaders_verified_email(self):
        """No email is sent when there are no errors."""
        factories.DataAffiliateAgreementFactory.create(is_primary=False)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        self.assertIn("Running Uploader audit... ok!", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_uploaders_needs_action_email(self):
        """Email is sent for one needs_action instance."""
        agreement = factories.DataAffiliateAgreementFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=agreement.signed_agreement.anvil_access_group,
        )
        account = AccountFactory.create(verified=True)
        agreement.uploaders.add(account.user)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        expected_output = "Running Uploader audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA UploaderAudit errors")
        self.assertIn(reverse("cdsa:audit:signed_agreements:uploaders:all"), email.alternatives[0][0])

    def test_command_uploaders_error_email(self):
        """Test command output with one error instance."""
        agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False)
        GroupGroupMembershipFactory.create(
            parent_group=agreement.anvil_upload_group,
        )
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        expected_output = "Running Uploader audit... problems found.\n* Verified: 0\n* Needs action: 0\n* Errors: 1\n"
        self.assertIn(expected_output, out.getvalue())
        self.assertIn(reverse("cdsa:audit:signed_agreements:uploaders:all"), out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA UploaderAudit errors")
        self.assertIn(reverse("cdsa:audit:signed_agreements:uploaders:all"), email.alternatives[0][0])

    def test_needs_action(self):
        agreement = factories.DataAffiliateAgreementFactory.create()
        factories.CDSAWorkspaceFactory.create(study=agreement.study)
        agreement.signed_agreement.accessors.add(AccountFactory.create(verified=True).user)
        agreement.uploaders.add(AccountFactory.create(verified=True).user)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", stdout=out)
        expected_output = (
            "Running CDSAWorkspace access audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        )
        self.assertIn(expected_output, out.getvalue())
        expected_output = (
            "Running SignedAgreement access audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        )
        self.assertIn(expected_output, out.getvalue())
        expected_output = "Running Accessor audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        expected_output = "Running Uploader audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        # No messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_needs_action_email(self):
        agreement = factories.DataAffiliateAgreementFactory.create()
        factories.CDSAWorkspaceFactory.create(study=agreement.study)
        agreement.signed_agreement.accessors.add(AccountFactory.create(verified=True).user)
        agreement.uploaders.add(AccountFactory.create(verified=True).user)
        out = StringIO()
        call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
        expected_output = (
            "Running CDSAWorkspace access audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        )
        self.assertIn(expected_output, out.getvalue())
        expected_output = (
            "Running SignedAgreement access audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        )
        self.assertIn(expected_output, out.getvalue())
        expected_output = "Running Accessor audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        expected_output = "Running Uploader audit... problems found.\n* Verified: 0\n* Needs action: 1\n* Errors: 0\n"
        self.assertIn(expected_output, out.getvalue())
        # Two messages has been sent.
        self.assertEqual(len(mail.outbox), 4)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA SignedAgreementAccessAudit errors")
        self.assertIn(reverse("cdsa:audit:signed_agreements:sag:all"), email.alternatives[0][0])
        email = mail.outbox[1]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA WorkspaceAccessAudit errors")
        self.assertIn(reverse("cdsa:audit:workspaces:all"), email.alternatives[0][0])
        email = mail.outbox[2]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA AccessorAudit errors")
        self.assertIn(reverse("cdsa:audit:signed_agreements:accessors:all"), email.alternatives[0][0])
        email = mail.outbox[3]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "CDSA UploaderAudit errors")
        self.assertIn(reverse("cdsa:audit:signed_agreements:uploaders:all"), email.alternatives[0][0])

    def test_different_domain(self):
        """Test command output when a different domain is specified."""
        site = Site.objects.create(domain="foobar.com", name="test")
        site.save()
        factories.DataAffiliateAgreementFactory.create()
        with self.settings(SITE_ID=site.id):
            out = StringIO()
            call_command("run_cdsa_audit", "--no-color", email="test@example.com", stdout=out)
            self.assertIn(
                "Running SignedAgreement access audit... problems found.",
                out.getvalue(),
            )
            self.assertIn("https://foobar.com", out.getvalue())
