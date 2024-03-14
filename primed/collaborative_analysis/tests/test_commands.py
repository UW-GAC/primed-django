"""Tests for management commands in the `dbgap` app."""

from io import StringIO

from anvil_consortium_manager.tests.factories import (
    GroupAccountMembershipFactory,
    GroupGroupMembershipFactory,
)
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.test import TestCase

from primed.dbgap.tests.factories import dbGaPWorkspaceFactory
from primed.miscellaneous_workspaces.tests.factories import OpenAccessWorkspaceFactory

from . import factories


class RunCollaborativeAnalysisAuditTest(TestCase):
    """Tests for the run_collaborative_analysis_audit command"""

    def test_command_output_no_records(self):
        """Test command output."""
        out = StringIO()
        call_command("run_collaborative_analysis_audit", "--no-color", stdout=out)
        self.assertIn(
            "Running Collaborative analysis access audit... ok!", out.getvalue()
        )
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 0", out.getvalue())
        self.assertIn("* Errors: 0", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_verified(self):
        """Test command output with one verified instance."""
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # One analyst without access.
        GroupAccountMembershipFactory.create(group=workspace.analyst_group)
        out = StringIO()
        call_command("run_collaborative_analysis_audit", "--no-color", stdout=out)
        self.assertIn(
            "Running Collaborative analysis access audit... ok!", out.getvalue()
        )
        self.assertIn("* Verified: 1", out.getvalue())
        self.assertIn("* Needs action: 0", out.getvalue())
        self.assertIn("* Errors: 0", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_needs_action(self):
        """Test command output with one needs_action instance."""
        source_workspace = OpenAccessWorkspaceFactory.create()
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # One analyst with access.
        GroupAccountMembershipFactory.create(group=workspace.analyst_group)
        out = StringIO()
        call_command("run_collaborative_analysis_audit", "--no-color", stdout=out)
        self.assertIn(
            "Running Collaborative analysis access audit... problems found.",
            out.getvalue(),
        )
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 1", out.getvalue())
        self.assertIn("* Errors: 0", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_error(self):
        """Test command output with one error instance."""
        source_workspace = OpenAccessWorkspaceFactory.create()
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # One group with unexpected access.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first()
        )
        out = StringIO()
        call_command("run_collaborative_analysis_audit", "--no-color", stdout=out)
        self.assertIn(
            "Running Collaborative analysis access audit... problems found.",
            out.getvalue(),
        )
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 0", out.getvalue())
        self.assertIn("* Errors: 1", out.getvalue())
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_verified_email(self):
        """No email is sent when there are no errors."""
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # One analyst without access.
        GroupAccountMembershipFactory.create(group=workspace.analyst_group)
        out = StringIO()
        call_command(
            "run_collaborative_analysis_audit",
            "--no-color",
            email="test@example.com",
            stdout=out,
        )
        self.assertIn(
            "Running Collaborative analysis access audit... ok!", out.getvalue()
        )
        # Zero messages have been sent by default.
        self.assertEqual(len(mail.outbox), 0)

    def test_command_run_audit_one_instance_needs_action_email(self):
        """Email is sent for one needs_action instance."""
        # Create a workspace and matching DAR.
        source_workspace = OpenAccessWorkspaceFactory.create()
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # One analyst with access.
        GroupAccountMembershipFactory.create(group=workspace.analyst_group)
        out = StringIO()
        call_command(
            "run_collaborative_analysis_audit",
            "--no-color",
            email="test@example.com",
            stdout=out,
        )
        self.assertIn(
            "Running Collaborative analysis access audit... problems found.",
            out.getvalue(),
        )
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 1", out.getvalue())
        self.assertIn("* Errors: 0", out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(
            email.subject, "Collaborative analysis access audit - problems found"
        )

    def test_command_run_audit_one_instance_error_email(self):
        """Test command output with one error instance."""
        # Create a workspace and matching DAR.
        source_workspace = OpenAccessWorkspaceFactory.create()
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # One group with unexpected access.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first()
        )
        out = StringIO()
        call_command(
            "run_collaborative_analysis_audit",
            "--no-color",
            email="test@example.com",
            stdout=out,
        )
        self.assertIn(
            "Running Collaborative analysis access audit... problems found.",
            out.getvalue(),
        )
        self.assertIn("* Verified: 0", out.getvalue())
        self.assertIn("* Needs action: 0", out.getvalue())
        self.assertIn("* Errors: 1", out.getvalue())
        # One message has been sent by default.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertEqual(
            email.subject, "Collaborative analysis access audit - problems found"
        )

    def test_different_domain(self):
        """Test command output when a different domain is specified."""
        site = Site.objects.create(domain="foobar.com", name="test")
        site.save()
        with self.settings(SITE_ID=site.id):
            source_workspace = OpenAccessWorkspaceFactory.create()
            workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
            workspace.source_workspaces.add(source_workspace.workspace)
            # One analyst with access.
            GroupAccountMembershipFactory.create(group=workspace.analyst_group)
            out = StringIO()
            call_command("run_collaborative_analysis_audit", "--no-color", stdout=out)
            self.assertIn(
                "Running Collaborative analysis access audit... problems found.",
                out.getvalue(),
            )
            self.assertIn("https://foobar.com", out.getvalue())
