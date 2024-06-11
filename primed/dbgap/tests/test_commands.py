"""Tests for management commands in the `dbgap` app."""

from io import StringIO

from anvil_consortium_manager.tests.factories import GroupGroupMembershipFactory
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.test import TestCase

from . import factories


class RunDbGaPAuditTest(TestCase):
    """Tests for the run_dbgap_audit command"""

    def test_command_output_no_records(self):
        """Test command output."""
        out = StringIO()
        call_command("run_dbgap_audit", "--no-color", stdout=out)
        self.assertIn("Running dbGaP access audit... ok!", out.getvalue())
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 0", out.getvalue())
        self.assertIn("* Errors: 0", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_verified(self):
        """Test command output with one verified instance."""
        # Create a workspace and matching DAR.
        factories.dbGaPWorkspaceFactory.create()
        factories.dbGaPApplicationFactory.create()
        out = StringIO()
        call_command("run_dbgap_audit", "--no-color", stdout=out)
        self.assertIn("Running dbGaP access audit... ok!", out.getvalue())
        self.assertIn("* Verified: 1", out.getvalue())
        self.assertIn("* Needs action: 0", out.getvalue())
        self.assertIn("* Errors: 0", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_needs_action(self):
        """Test command output with one needs_action instance."""
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=dbgap_workspace)
        out = StringIO()
        call_command("run_dbgap_audit", "--no-color", stdout=out)
        self.assertIn("Running dbGaP access audit... problems found.", out.getvalue())
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 1", out.getvalue())
        self.assertIn("* Errors: 0", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_error(self):
        """Test command output with one error instance."""
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dbgap_application.anvil_access_group,
        )
        out = StringIO()
        call_command("run_dbgap_audit", "--no-color", stdout=out)
        self.assertIn("Running dbGaP access audit... problems found.", out.getvalue())
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 0", out.getvalue())
        self.assertIn("* Errors: 1", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_verified_email(self):
        """No email is sent when there are no errors."""
        # Create a workspace and matching DAR.
        factories.dbGaPWorkspaceFactory.create()
        factories.dbGaPApplicationFactory.create()
        out = StringIO()
        call_command("run_dbgap_audit", "--no-color", email="test@example.com", stdout=out)
        self.assertIn("Running dbGaP access audit... ok!", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_needs_action_email(self):
        """Email is sent for one needs_action instance."""
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=dbgap_workspace)
        out = StringIO()
        call_command("run_dbgap_audit", "--no-color", email="test@example.com", stdout=out)
        self.assertIn("Running dbGaP access audit... problems found.", out.getvalue())
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 1", out.getvalue())
        self.assertIn("* Errors: 0", out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "dbGaP access audit - problems found")

    def test_command_run_audit_one_instance_error_email(self):
        """Test command output with one error instance."""
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dbgap_application.anvil_access_group,
        )
        out = StringIO()
        call_command("run_dbgap_audit", "--no-color", email="test@example.com", stdout=out)
        self.assertIn("Running dbGaP access audit... problems found.", out.getvalue())
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 0", out.getvalue())
        self.assertIn("* Errors: 1", out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(email.subject, "dbGaP access audit - problems found")

    def test_different_domain(self):
        """Test command output when a different domain is specified."""
        site = Site.objects.create(domain="foobar.com", name="test")
        site.save()
        with self.settings(SITE_ID=site.id):
            dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
            factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=dbgap_workspace)
            out = StringIO()
            call_command("run_dbgap_audit", "--no-color", stdout=out)
            self.assertIn("Running dbGaP access audit... problems found.", out.getvalue())
            self.assertIn("https://foobar.com", out.getvalue())

    def test_command_collaborator_audit(self):
        """run_dbgap_audit runs an audit on collaborators."""
        self.fail()
