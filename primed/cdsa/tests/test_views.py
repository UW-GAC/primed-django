"""Tests for views related to the `cdsa` app."""

from datetime import date, timedelta

import responses
from anvil_consortium_manager.models import (
    AnVILProjectManagerAccess,
    GroupGroupMembership,
    ManagedGroup,
    Workspace,
)
from anvil_consortium_manager.tests.api_factories import ErrorResponseFactory
from anvil_consortium_manager.tests.factories import (
    BillingProjectFactory,
    GroupAccountMembershipFactory,
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
)
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core.exceptions import NON_FIELD_ERRORS, PermissionDenied
from django.http import Http404
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from primed.duo.tests.factories import DataUseModifierFactory, DataUsePermissionFactory
from primed.primed_anvil.tests.factories import (
    AvailableDataFactory,
    StudyFactory,
    StudySiteFactory,
)
from primed.users.tests.factories import UserFactory

from .. import forms, models, tables, views
from ..audit import signed_agreement_audit, workspace_audit
from . import factories

User = get_user_model()


class NavbarTest(TestCase):
    """Tests for the navbar involving CDSA links."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:index", args=args)

    def test_links_for_staff_view(self):
        """Returns successful response code."""
        user = User.objects.create_user(username="test", password="test")
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url())
        self.assertContains(response, reverse("cdsa:agreement_versions:list"))
        self.assertContains(response, reverse("cdsa:audit:signed_agreements:all"))
        self.assertContains(response, reverse("cdsa:audit:workspaces:all"))
        self.assertContains(response, reverse("cdsa:records:index"))
        # Links to add CDSAs.
        self.assertNotContains(response, reverse("cdsa:signed_agreements:members:new"))
        self.assertNotContains(
            response, reverse("cdsa:signed_agreements:data_affiliates:new")
        )
        self.assertNotContains(
            response, reverse("cdsa:signed_agreements:non_data_affiliates:new")
        )

    def test_links_for_staff_edit(self):
        """Returns successful response code."""
        user = User.objects.create_user(username="test", password="test")
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url())
        self.assertContains(response, reverse("cdsa:agreement_versions:list"))
        self.assertContains(response, reverse("cdsa:audit:signed_agreements:all"))
        self.assertContains(response, reverse("cdsa:audit:workspaces:all"))
        self.assertContains(response, reverse("cdsa:records:index"))
        # Links to add CDSAs.
        self.assertContains(response, reverse("cdsa:signed_agreements:members:new"))
        self.assertContains(
            response, reverse("cdsa:signed_agreements:data_affiliates:new")
        )
        self.assertContains(
            response, reverse("cdsa:signed_agreements:non_data_affiliates:new")
        )


class AgreementVersionListTest(TestCase):
    """Tests for the AgreementVersionList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreement_versions:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.AgreementVersionList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(
            response.context_data["table"], tables.AgreementVersionTable
        )

    def test_workspace_table_none(self):
        """No rows are shown if there are no AgreementVersion objects."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_workspace_table_three(self):
        """Two rows are shown if there are three AgreementVersion objects."""
        factories.AgreementVersionFactory.create_batch(3)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 3)


class AgreementMajorVersionDetailTest(TestCase):
    """Tests for the AgreementVersionDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        # Create an object test this with.
        self.obj = factories.AgreementMajorVersionFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreement_versions:major_version_detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.AgreementMajorVersionDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(2))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(2),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(2))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, major_version=2)

    def test_view_status_code_with_existing_object(self):
        """Returns a successful status code for an existing object pk."""
        # Only clients load the template.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)

    def test_view_status_code_with_invalid_version(self):
        """Raises a 404 error with an invalid major and minor version."""
        request = self.factory.get(self.get_url(self.obj.version + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                major_version=self.obj.version + 1,
            )

    def test_context_table_classes(self):
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)
        self.assertIn("tables", response.context_data)
        self.assertEqual(len(response.context_data["tables"]), 2)
        self.assertIsInstance(
            response.context_data["tables"][0], tables.AgreementVersionTable
        )
        self.assertIsInstance(
            response.context_data["tables"][1], tables.SignedAgreementTable
        )

    def test_response_includes_agreement_version_table(self):
        """agreement_version_table includes agreement_versions with this major version."""
        factories.AgreementVersionFactory.create(major_version=self.obj)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(len(response.context_data["tables"][0].rows), 1)

    def test_response_includes_agreement_version_table_other_major_version(self):
        """agreement_version_table includes only agreement_versions with this major version."""
        other_agreement = factories.AgreementVersionFactory.create(
            major_version__version=self.obj.version + 1
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(len(response.context_data["tables"][0].rows), 0)
        self.assertNotIn(other_agreement, response.context_data["tables"][0].data)

    def test_response_signed_agreement_table_three_agreements(self):
        """signed_agreement_table includes all types of agreements."""
        factories.MemberAgreementFactory.create(
            signed_agreement__version__major_version__version=self.obj.version
        )
        factories.DataAffiliateAgreementFactory.create(
            signed_agreement__version__major_version__version=self.obj.version
        )
        factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__version__major_version__version=self.obj.version
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data["tables"][1].rows), 3)

    def test_response_signed_agreement_table_other_major_version(self):
        """signed_agreement_table does not include agreements from other versions."""
        factories.MemberAgreementFactory.create()
        factories.DataAffiliateAgreementFactory.create()
        factories.NonDataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data["tables"][1].rows), 0)

    def test_response_show_deprecation_message_valid(self):
        """response context does not show a deprecation warning when AgreementMajorVersion is valid."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertFalse(response.context_data["show_deprecation_message"])
        self.assertNotIn(b"Deprecated", response.content)

    def test_response_show_deprecation_message_not_valid(self):
        """response context does show a deprecation warning when AgreementMajorVersion is is not valid."""
        self.obj.is_valid = False
        self.obj.save()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertTrue(response.context_data["show_deprecation_message"])
        self.assertIn(b"Deprecated", response.content)

    def test_invalidate_button_valid_user_has_edit_perm(self):
        """Invalidate button appears when the user has edit permission and the instance is valid."""
        user = User.objects.create_user(username="test_edit", password="test_edit")
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_invalidate_button", response.context_data)
        self.assertTrue(response.context_data["show_invalidate_button"])
        self.assertContains(
            response,
            reverse("cdsa:agreement_versions:invalidate", args=[self.obj.version]),
        )

    def test_invalidate_button_valid_user_has_view_perm(self):
        """Invalidate button does not appear when the user has view permission and the instance is valid."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_invalidate_button", response.context_data)
        self.assertFalse(response.context_data["show_invalidate_button"])
        self.assertNotContains(
            response,
            reverse("cdsa:agreement_versions:invalidate", args=[self.obj.version]),
        )

    def test_invalidate_button_invalid_user_has_edit_perm(self):
        """Invalidate button does not appear when the user has edit permission and the instance is invalid."""
        self.obj.is_valid = False
        self.obj.save()
        user = User.objects.create_user(username="test_edit", password="test_edit")
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_invalidate_button", response.context_data)
        self.assertFalse(response.context_data["show_invalidate_button"])
        self.assertNotContains(
            response,
            reverse("cdsa:agreement_versions:invalidate", args=[self.obj.version]),
        )

    def test_invalidate_button_invalid_user_has_view_perm(self):
        """Invalidate button does not appear when the user has view permission and the instance is invalid."""
        self.obj.is_valid = False
        self.obj.save()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.version))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_invalidate_button", response.context_data)
        self.assertFalse(response.context_data["show_invalidate_button"])
        self.assertNotContains(
            response,
            reverse("cdsa:agreement_versions:invalidate", args=[self.obj.version]),
        )


class AgreementMajorVersionInvalidateTest(TestCase):
    """Tests for the AgreementMajorVersionInvalidate view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreement_versions:invalidate", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.AgreementMajorVersionInvalidate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1)
        )

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        instance = factories.AgreementMajorVersionFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.version))
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, major_version=1)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has only view permission."""
        instance = factories.AgreementMajorVersionFactory.create()
        user_view_perm = User.objects.create_user(
            username="test-none", password="test-none"
        )
        user_view_perm.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url(instance.version))
        request.user = user_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, major_version=instance.version)

    def test_object_does_not_exist(self):
        request = self.factory.get(self.get_url(1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, major_version=1)

    def test_has_object_in_context(self):
        """Response includes a form."""
        instance = factories.AgreementMajorVersionFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.version))
        self.assertTrue("object" in response.context_data)
        self.assertEqual(response.context_data["object"], instance)

    def test_has_form_in_context(self):
        """Response includes a form."""
        instance = factories.AgreementMajorVersionFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.version))
        self.assertTrue("form" in response.context_data)

    def test_form_class(self):
        """Form is the expected class."""
        instance = factories.AgreementMajorVersionFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.version))
        self.assertIsInstance(
            response.context_data["form"], forms.AgreementMajorVersionIsValidForm
        )

    def test_invalidates_instance(self):
        """Can invalidate the instance."""
        instance = factories.AgreementMajorVersionFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.version), {})
        self.assertEqual(response.status_code, 302)
        instance.refresh_from_db()
        self.assertFalse(instance.is_valid)

    def test_sets_one_signed_agreement_to_lapsed(self):
        """Sets SignedAgreements associated with this major version to LAPSED."""
        instance = factories.AgreementMajorVersionFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(
            version__major_version=instance
        )
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.version), {})
        self.assertEqual(response.status_code, 302)
        signed_agreement.refresh_from_db()
        self.assertEqual(
            signed_agreement.status, models.SignedAgreement.StatusChoices.LAPSED
        )

    def test_sets_two_signed_agreements_to_lapsed(self):
        """Sets SignedAgreements associated with this major version to LAPSED."""
        instance = factories.AgreementMajorVersionFactory.create()
        signed_agreement_1 = factories.SignedAgreementFactory.create(
            version__major_version=instance
        )
        signed_agreement_2 = factories.SignedAgreementFactory.create(
            version__major_version=instance
        )
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.version), {})
        self.assertEqual(response.status_code, 302)
        signed_agreement_1.refresh_from_db()
        self.assertEqual(
            signed_agreement_1.status, models.SignedAgreement.StatusChoices.LAPSED
        )
        signed_agreement_2.refresh_from_db()
        self.assertEqual(
            signed_agreement_2.status, models.SignedAgreement.StatusChoices.LAPSED
        )

    def test_only_sets_active_signed_agreements_to_lapsed(self):
        """Does not set SignedAgreements with a different status to LAPSED."""
        instance = factories.AgreementMajorVersionFactory.create()
        withdrawn_agreement = factories.SignedAgreementFactory.create(
            version__major_version=instance,
            status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        lapsed_agreement = factories.SignedAgreementFactory.create(
            version__major_version=instance,
            status=models.SignedAgreement.StatusChoices.LAPSED,
        )
        replaced_agreement = factories.SignedAgreementFactory.create(
            version__major_version=instance,
            status=models.SignedAgreement.StatusChoices.REPLACED,
        )
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.version), {})
        self.assertEqual(response.status_code, 302)
        lapsed_agreement.refresh_from_db()
        self.assertEqual(
            lapsed_agreement.status, models.SignedAgreement.StatusChoices.LAPSED
        )
        withdrawn_agreement.refresh_from_db()
        self.assertEqual(
            withdrawn_agreement.status, models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        replaced_agreement.refresh_from_db()
        self.assertEqual(
            replaced_agreement.status, models.SignedAgreement.StatusChoices.REPLACED
        )

    def test_only_sets_associated_signed_agreements_to_lapsed(self):
        """Does not set SignedAgreements associated with a different version to LAPSED."""
        instance = factories.AgreementMajorVersionFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.version), {})
        self.assertEqual(response.status_code, 302)
        signed_agreement.refresh_from_db()
        self.assertEqual(
            signed_agreement.status, models.SignedAgreement.StatusChoices.ACTIVE
        )

    def test_redirect_url(self):
        """Redirects to successful url."""
        instance = factories.AgreementMajorVersionFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.version), {})
        self.assertRedirects(response, instance.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        instance = factories.AgreementMajorVersionFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.version), {})
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.AgreementMajorVersionInvalidate.success_message, str(messages[0])
        )

    def test_version_already_invalid_get(self):
        instance = factories.AgreementMajorVersionFactory.create(is_valid=False)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.version))
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.AgreementMajorVersionInvalidate.ERROR_ALREADY_INVALID,
            str(messages[0]),
        )

    def test_version_already_invalid_post(self):
        instance = factories.AgreementMajorVersionFactory.create(is_valid=False)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.version), {})
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.AgreementMajorVersionInvalidate.ERROR_ALREADY_INVALID,
            str(messages[0]),
        )


class AgreementVersionDetailTest(TestCase):
    """Tests for the AgreementVersionDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        # Create an object test this with.
        self.obj = factories.AgreementVersionFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreement_versions:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.AgreementVersionDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(2, 5))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(2, 5),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(self.obj.major_version.version, self.obj.minor_version)
        )
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(2, 5))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, major_version=2, minor_version=5)

    def test_view_status_code_with_existing_object(self):
        """Returns a successful status code for an existing object pk."""
        # Only clients load the template.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(self.obj.major_version.version, self.obj.minor_version)
        )
        self.assertEqual(response.status_code, 200)

    def test_view_status_code_with_invalid_version(self):
        """Raises a 404 error with an invalid major and minor version."""
        request = self.factory.get(
            self.get_url(self.obj.major_version.version + 1, self.obj.minor_version + 1)
        )
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                major_version=self.obj.major_version.version + 1,
                minor_version=self.obj.minor_version + 1,
            )

    def test_view_status_code_with_other_major_version(self):
        """Raises a 404 error with an invalid object major version."""
        request = self.factory.get(
            self.get_url(self.obj.major_version.version + 1, self.obj.minor_version)
        )
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                major_version__version=self.obj.major_version.version + 1,
                minor_version=self.obj.minor_version,
            )

    def test_view_status_code_with_other_minor_version(self):
        """Raises a 404 error with an invalid object minor version."""
        request = self.factory.get(
            self.get_url(self.obj.major_version.version, self.obj.minor_version + 1)
        )
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                major_version=self.obj.major_version.version,
                minor_version=self.obj.minor_version + 1,
            )

    # def test_response_includes_link_to_major_agreement(self):
    #     """Response includes a link to the user profile page."""
    #     self.client.force_login(self.user)
    #     response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
    #     self.assertContains(
    #         response, self.obj.signed_agreement.representative.get_absolute_url()
    #     )

    def test_response_includes_signed_agreement_table(self):
        """Response includes a table of SignedAgreements."""
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(self.obj.major_version.version, self.obj.minor_version)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("signed_agreement_table", response.context_data)
        self.assertIsInstance(
            response.context_data["signed_agreement_table"], tables.SignedAgreementTable
        )

    def test_response_signed_agreement_table_three_agreements(self):
        """signed_agreement_table includes all types of agreements."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__version=self.obj
        )
        da_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__version=self.obj
        )
        nda_agreement = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__version=self.obj
        )
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(self.obj.major_version.version, self.obj.minor_version)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data["signed_agreement_table"].rows), 3)
        self.assertIn(
            member_agreement.signed_agreement,
            response.context_data["signed_agreement_table"].data,
        )
        self.assertIn(
            da_agreement.signed_agreement,
            response.context_data["signed_agreement_table"].data,
        )
        self.assertIn(
            nda_agreement.signed_agreement,
            response.context_data["signed_agreement_table"].data,
        )

    def test_response_signed_agreement_table_other_version(self):
        """signed_agreement_table does not include agreements from other versions."""
        member_agreement = factories.MemberAgreementFactory.create()
        da_agreement = factories.DataAffiliateAgreementFactory.create()
        nda_agreement = factories.NonDataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(self.obj.major_version.version, self.obj.minor_version)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data["signed_agreement_table"].rows), 0)
        self.assertNotIn(
            member_agreement.signed_agreement,
            response.context_data["signed_agreement_table"].data,
        )
        self.assertNotIn(
            da_agreement.signed_agreement,
            response.context_data["signed_agreement_table"].data,
        )
        self.assertNotIn(
            nda_agreement.signed_agreement,
            response.context_data["signed_agreement_table"].data,
        )

    def test_response_show_deprecation_message_valid(self):
        """response context does not show a deprecation warning when AgreementMajorVersion is valid."""
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(self.obj.major_version.version, self.obj.minor_version)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertFalse(response.context_data["show_deprecation_message"])
        self.assertNotIn(b"Deprecated", response.content)

    def test_response_show_deprecation_message_not_valid(self):
        """response context does show a deprecation warning when AgreementMajorVersion is not valid."""
        self.obj.major_version.is_valid = False
        self.obj.major_version.save()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(self.obj.major_version.version, self.obj.minor_version)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertTrue(response.context_data["show_deprecation_message"])
        self.assertIn(b"Deprecated", response.content)


class SignedAgreementListTest(TestCase):
    """Tests for the SignedAgreementList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.SignedAgreementList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(
            response.context_data["table"], tables.SignedAgreementTable
        )

    def test_workspace_table_none(self):
        """No rows are shown if there are no SignedAgreement objects."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_workspace_table_three(self):
        """Two rows are shown if there are three SignedAgreement objects."""
        factories.MemberAgreementFactory.create()
        factories.DataAffiliateAgreementFactory.create()
        factories.NonDataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 3)


class SignedAgreementStatusUpdateMemberTest(TestCase):
    """Tests for the SignedAgreementStatusUpdate view with a MemberAgreement."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:members:update", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.SignedAgreementStatusUpdate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        instance = factories.MemberAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)

    def test_access_with_view_permission(self):
        """Raises permission denied if user has only view permission."""
        user_with_view_perm = User.objects.create_user(
            username="test-other", password="test-other"
        )
        user_with_view_perm.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_with_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, cc_id=1)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, cc_id=1)

    def test_object_does_not_exist(self):
        """Raises Http404 if object does not exist."""
        request = self.factory.get(self.get_url(1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, cc_id=1)

    def test_object_different_agreement_type(self):
        """Raises Http404 if object has a different agreement type."""
        instance = factories.DataAffiliateAgreementFactory.create()
        request = self.factory.get(self.get_url(instance.signed_agreement.cc_id))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, cc_id=instance.signed_agreement.cc_id)

    def test_has_form_in_context(self):
        """Response includes a form."""
        instance = factories.MemberAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.signed_agreement.cc_id))
        self.assertTrue("form" in response.context_data)
        self.assertIsInstance(
            response.context_data["form"], forms.SignedAgreementStatusForm
        )

    def test_can_modify_status(self):
        """Can change the status."""
        instance = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id),
            {"status": models.SignedAgreement.StatusChoices.WITHDRAWN},
        )
        self.assertEqual(response.status_code, 302)
        instance.refresh_from_db()
        self.assertEqual(
            instance.signed_agreement.status,
            models.SignedAgreement.StatusChoices.WITHDRAWN,
        )

    def test_invalid_status(self):
        """Can change the status."""
        instance = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id), {"status": "foo"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("status", form.errors)
        self.assertEqual(len(form.errors["status"]), 1)
        self.assertIn("valid choice", form.errors["status"][0])
        instance.refresh_from_db()
        self.assertEqual(
            instance.signed_agreement.status,
            models.SignedAgreement.StatusChoices.ACTIVE,
        )

    def test_success_message(self):
        """Response includes a success message if successful."""
        instance = factories.MemberAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id),
            {"status": models.SignedAgreement.StatusChoices.WITHDRAWN},
            follow=True,
        )
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.SignedAgreementStatusUpdate.success_message, str(messages[0])
        )

    def test_redirects_to_object_detail(self):
        """After successfully creating an object, view redirects to the object's detail page."""
        # This needs to use the client because the RequestFactory doesn't handle redirects.
        instance = factories.MemberAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id),
            {"status": models.SignedAgreement.StatusChoices.WITHDRAWN},
        )
        self.assertRedirects(response, instance.get_absolute_url())


class SignedAgreementStatusUpdateDataAffiliateTest(TestCase):
    """Tests for the SignedAgreementStatusUpdate view with a DataAffiliateAgreement."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:data_affiliates:update", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.SignedAgreementStatusUpdate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        instance = factories.DataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)

    def test_access_with_view_permission(self):
        """Raises permission denied if user has only view permission."""
        user_with_view_perm = User.objects.create_user(
            username="test-other", password="test-other"
        )
        user_with_view_perm.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_with_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, cc_id=1)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, cc_id=1)

    def test_object_does_not_exist(self):
        """Raises Http404 if object does not exist."""
        request = self.factory.get(self.get_url(1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, cc_id=1)

    def test_object_different_agreement_type(self):
        """Raises Http404 if object has a different agreement type."""
        instance = factories.MemberAgreementFactory.create()
        request = self.factory.get(self.get_url(instance.signed_agreement.cc_id))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, cc_id=instance.signed_agreement.cc_id)

    def test_has_form_in_context(self):
        """Response includes a form."""
        instance = factories.DataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.signed_agreement.cc_id))
        self.assertTrue("form" in response.context_data)
        self.assertIsInstance(
            response.context_data["form"], forms.SignedAgreementStatusForm
        )

    def test_can_modify_status(self):
        """Can change the status."""
        instance = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id),
            {"status": models.SignedAgreement.StatusChoices.WITHDRAWN},
        )
        self.assertEqual(response.status_code, 302)
        instance.refresh_from_db()
        self.assertEqual(
            instance.signed_agreement.status,
            models.SignedAgreement.StatusChoices.WITHDRAWN,
        )

    def test_invalid_status(self):
        """Can change the status."""
        instance = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id), {"status": "foo"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("status", form.errors)
        self.assertEqual(len(form.errors["status"]), 1)
        self.assertIn("valid choice", form.errors["status"][0])
        instance.refresh_from_db()
        self.assertEqual(
            instance.signed_agreement.status,
            models.SignedAgreement.StatusChoices.ACTIVE,
        )

    def test_success_message(self):
        """Response includes a success message if successful."""
        instance = factories.DataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id),
            {"status": models.SignedAgreement.StatusChoices.WITHDRAWN},
            follow=True,
        )
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.SignedAgreementStatusUpdate.success_message, str(messages[0])
        )

    def test_redirects_to_object_detail(self):
        """After successfully creating an object, view redirects to the object's detail page."""
        # This needs to use the client because the RequestFactory doesn't handle redirects.
        instance = factories.DataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id),
            {"status": models.SignedAgreement.StatusChoices.WITHDRAWN},
        )
        self.assertRedirects(response, instance.get_absolute_url())


class SignedAgreementStatusUpdateNonDataAffiliateTest(TestCase):
    """Tests for the SignedAgreementStatusUpdate view with a NonDataAffiliateAgreement."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:non_data_affiliates:update", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.SignedAgreementStatusUpdate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        instance = factories.NonDataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)

    def test_access_with_view_permission(self):
        """Raises permission denied if user has only view permission."""
        user_with_view_perm = User.objects.create_user(
            username="test-other", password="test-other"
        )
        user_with_view_perm.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_with_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, cc_id=1)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, cc_id=1)

    def test_object_does_not_exist(self):
        """Raises Http404 if object does not exist."""
        request = self.factory.get(self.get_url(1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, cc_id=1)

    def test_object_different_agreement_type(self):
        """Raises Http404 if object has a different agreement type."""
        instance = factories.MemberAgreementFactory.create()
        request = self.factory.get(self.get_url(instance.signed_agreement.cc_id))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, cc_id=instance.signed_agreement.cc_id)

    def test_has_form_in_context(self):
        """Response includes a form."""
        instance = factories.NonDataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.signed_agreement.cc_id))
        self.assertTrue("form" in response.context_data)
        self.assertIsInstance(
            response.context_data["form"], forms.SignedAgreementStatusForm
        )

    def test_can_modify_status(self):
        """Can change the status."""
        instance = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id),
            {"status": models.SignedAgreement.StatusChoices.WITHDRAWN},
        )
        self.assertEqual(response.status_code, 302)
        instance.refresh_from_db()
        self.assertEqual(
            instance.signed_agreement.status,
            models.SignedAgreement.StatusChoices.WITHDRAWN,
        )

    def test_invalid_status(self):
        """Can change the status."""
        instance = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id), {"status": "foo"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("status", form.errors)
        self.assertEqual(len(form.errors["status"]), 1)
        self.assertIn("valid choice", form.errors["status"][0])
        instance.refresh_from_db()
        self.assertEqual(
            instance.signed_agreement.status,
            models.SignedAgreement.StatusChoices.ACTIVE,
        )

    def test_success_message(self):
        """Response includes a success message if successful."""
        instance = factories.NonDataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id),
            {"status": models.SignedAgreement.StatusChoices.WITHDRAWN},
            follow=True,
        )
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.SignedAgreementStatusUpdate.success_message, str(messages[0])
        )

    def test_redirects_to_object_detail(self):
        """After successfully creating an object, view redirects to the object's detail page."""
        # This needs to use the client because the RequestFactory doesn't handle redirects.
        instance = factories.NonDataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(instance.signed_agreement.cc_id),
            {"status": models.SignedAgreement.StatusChoices.WITHDRAWN},
        )
        self.assertRedirects(response, instance.get_absolute_url())


class MemberAgreementCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for the MemberAgreementCreate view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        # Create the admins group.
        self.cc_admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:members:new", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.MemberAgreementCreate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has only view permission."""
        user_view_perm = User.objects.create_user(
            username="test-none", password="test-none"
        )
        user_view_perm.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url())
        request.user = user_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_has_forms_in_context(self):
        """Response includes a form."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertTrue("form" in response.context_data)
        self.assertTrue("formset" in response.context_data)

    def test_form_classes(self):
        """Form is the expected class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIsInstance(response.context_data["form"], forms.SignedAgreementForm)
        self.assertEqual(len(response.context_data["formset"].forms), 1)
        self.assertIsInstance(
            response.context_data["formset"].forms[0], forms.MemberAgreementForm
        )

    def test_can_create_object(self):
        """Can create an object."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # New objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 1)
        new_agreement = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(new_agreement.cc_id, 1234)
        self.assertEqual(new_agreement.representative, representative)
        self.assertEqual(new_agreement.representative_role, "Test role")
        self.assertEqual(new_agreement.signing_institution, "Test institution")
        self.assertEqual(new_agreement.date_signed, date.fromisoformat("2023-01-01"))
        self.assertEqual(new_agreement.is_primary, True)
        # Type was set correctly.
        self.assertEqual(new_agreement.type, new_agreement.MEMBER)
        # AnVIL group was set correctly.
        self.assertIsInstance(new_agreement.anvil_access_group, ManagedGroup)
        self.assertEqual(
            new_agreement.anvil_access_group.name, "TEST_PRIMED_CDSA_ACCESS_1234"
        )
        self.assertEqual(
            new_agreement.status, models.SignedAgreement.StatusChoices.ACTIVE
        )
        # Check the agreement type.
        self.assertEqual(models.MemberAgreement.objects.count(), 1)
        new_agreement_type = models.MemberAgreement.objects.latest("pk")
        self.assertEqual(new_agreement.memberagreement, new_agreement_type)
        self.assertEqual(new_agreement_type.study_site, study_site)

    def test_redirect_url(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertRedirects(response, new_object.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.MemberAgreementCreate.success_message, str(messages[0]))

    def test_error_missing_cc_id(self):
        """Form shows an error when cc_id is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                # "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("required", form.errors["cc_id"][0])

    def test_invalid_cc_id(self):
        """Form shows an error when cc_id is invalid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": -1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)

    def test_error_missing_representative(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                # "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative", form.errors)
        self.assertEqual(len(form.errors["representative"]), 1)
        self.assertIn("required", form.errors["representative"][0])

    def test_error_invalid_representative(self):
        """Form shows an error when representative is invalid."""
        self.client.force_login(self.user)
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": 9999,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative", form.errors)
        self.assertEqual(len(form.errors["representative"]), 1)
        self.assertIn("valid", form.errors["representative"][0])

    def test_error_missing_representative_role(self):
        """Form shows an error when representative_role is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                # "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative_role", form.errors)
        self.assertEqual(len(form.errors["representative_role"]), 1)
        self.assertIn("required", form.errors["representative_role"][0])

    def test_error_missing_signing_institution(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                # "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("signing_institution", form.errors)
        self.assertEqual(len(form.errors["signing_institution"]), 1)
        self.assertIn("required", form.errors["signing_institution"][0])

    def test_error_missing_version(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                # "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("required", form.errors["version"][0])

    def test_error_invalid_version(self):
        """Form shows an error when version is invalid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": 999,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("valid", form.errors["version"][0])

    def test_error_missing_date_signed(self):
        """Form shows an error when date_signed is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                # "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("date_signed", form.errors)
        self.assertEqual(len(form.errors["date_signed"]), 1)
        self.assertIn("required", form.errors["date_signed"][0])

    def test_error_missing_is_primary(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                # "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("is_primary", form.errors)
        self.assertEqual(len(form.errors["is_primary"]), 1)
        self.assertIn("required", form.errors["is_primary"][0])

    def test_error_missing_memberagreement_study_site(self):
        """Form shows an error when study_site is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                # "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertTrue(form.is_valid())
        formset = response.context_data["formset"]
        self.assertFalse(formset.is_valid())
        self.assertFalse(formset.forms[0].is_valid())
        self.assertEqual(len(formset.forms[0].errors), 1)
        self.assertIn("study_site", formset.forms[0].errors)
        self.assertEqual(len(formset.forms[0].errors["study_site"]), 1)
        self.assertIn("required", formset.forms[0].errors["study_site"][0])

    def test_error_invalid_memberagreement_study_site(self):
        """Form shows an error when study_site is invalid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": 999,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        form = response.context_data["form"]
        self.assertTrue(form.is_valid())
        formset = response.context_data["formset"]
        self.assertFalse(formset.is_valid())
        self.assertEqual(len(formset.forms[0].errors), 1)
        self.assertIn("study_site", formset.forms[0].errors)
        self.assertEqual(len(formset.forms[0].errors["study_site"]), 1)
        self.assertIn("valid", formset.forms[0].errors["study_site"][0])

    def test_error_duplicate_project_id(self):
        """Form shows an error when trying to create a duplicate dbgap_phs."""
        obj = factories.MemberAgreementFactory.create()
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": obj.signed_agreement.cc_id,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(
            models.SignedAgreement.objects.count(), 1
        )  # One already existed.
        self.assertEqual(
            models.MemberAgreement.objects.count(), 1
        )  # One already existed.
        # Form has errors in the correct field.
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("already exists", form.errors["cc_id"][0])

    def test_post_blank_data(self):
        """Posting blank data does not create an object."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {})
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())

    def test_creates_anvil_access_group(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(ManagedGroup.objects.count(), 2)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "TEST_PRIMED_CDSA_ACCESS_2345")
        self.assertTrue(new_group.is_managed_by_app)
        # A group-group membership was created with PRIMED_CC_ADMINS as an admin of the access group.
        new_membership = GroupGroupMembership.objects.get(
            parent_group=new_object.anvil_access_group, child_group=self.cc_admins_group
        )
        self.assertEqual(new_membership.role, GroupGroupMembership.ADMIN)

    @override_settings(ANVIL_DATA_ACCESS_GROUP_PREFIX="foo")
    def test_creates_anvil_groups_different_setting_access_group_prefix(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        api_url = (
            self.api_client.sam_entry_point + "/api/groups/v1/foo_CDSA_ACCESS_2345"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/foo_CDSA_ACCESS_2345/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(ManagedGroup.objects.count(), 2)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "foo_CDSA_ACCESS_2345")
        self.assertTrue(new_group.is_managed_by_app)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foo")
    def test_creates_anvil_groups_different_setting_cc_admins_group_name(self):
        """View creates a managed group upon when form is valid."""
        admin_group = ManagedGroupFactory.create(name="foo", email="foo@firecloud.org")
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345/admin/foo@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        membership = GroupGroupMembership.objects.get(
            parent_group=new_object.anvil_access_group,
            child_group=admin_group,
        )
        self.assertEqual(membership.role, GroupGroupMembership.ADMIN)

    def test_manage_group_create_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating the group."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = (
            self.api_client.sam_entry_point + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=500, json={"message": "other error"}
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        formset = response.context["formset"]
        self.assertTrue(formset.is_valid())
        # ...but there was some error from the API.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual("AnVIL API Error: other error", str(messages[0]))
        # No objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        self.assertEqual(ManagedGroup.objects.count(), 1)  # Just the admins group.

    def test_managed_group_already_exists_in_app(self):
        """No objects are created if the managed group already exists in the app."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        # Create a group with the same name.
        ManagedGroupFactory.create(name="TEST_PRIMED_CDSA_ACCESS_1")
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        # ...but there was an error with the group name.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.MemberAgreementCreate.ERROR_CREATING_GROUP, str(messages[0])
        )
        # No dbGaPApplication was created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)

    def test_admin_group_membership_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating admin group membership."""
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            api_url + "/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=400,
            json={"message": "other error"},
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        formset = response.context["formset"]
        self.assertTrue(formset.is_valid())
        # ...but there was some error from the API.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual("AnVIL API Error: other error", str(messages[0]))
        # No objects were created.
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        self.assertEqual(ManagedGroup.objects.count(), 1)  # Just the admin group.


class MemberAgreementDetailTest(TestCase):
    """Tests for the MemberAgreementDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        # Create an object test this with.
        self.obj = factories.MemberAgreementFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:members:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.MemberAgreementDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, cc_id=1)

    def test_view_status_code_with_existing_object(self):
        """Returns a successful status code for an existing object pk."""
        # Only clients load the template.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)

    def test_view_status_code_with_invalid_pk(self):
        """Raises a 404 error with an invalid object pk."""
        request = self.factory.get(self.get_url(self.obj.signed_agreement.cc_id + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, pk=self.obj.signed_agreement.cc_id + 1)

    def test_response_includes_link_to_user_profile(self):
        """Response includes a link to the user profile page."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertContains(
            response, self.obj.signed_agreement.representative.get_absolute_url()
        )

    def test_response_includes_link_to_study_site(self):
        """Response includes a link to the study site detail page."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertContains(response, self.obj.study_site.get_absolute_url())

    def test_response_includes_link_to_anvil_access_group(self):
        """Response includes a link to the AnVIL access group detail page."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertContains(
            response, self.obj.signed_agreement.anvil_access_group.get_absolute_url()
        )

    def test_response_show_deprecation_message_valid(self):
        """response context does not show a deprecation warning when AgreementMajorVersion is valid."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertFalse(response.context_data["show_deprecation_message"])
        self.assertNotIn(b"Deprecated CDSA version", response.content)

    def test_response_show_deprecation_message_not_valid(self):
        """response context does show a deprecation warning when AgreementMajorVersion is not valid."""
        self.obj.signed_agreement.version.major_version.is_valid = False
        self.obj.signed_agreement.version.major_version.save()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertTrue(response.context_data["show_deprecation_message"])
        self.assertIn(b"Deprecated CDSA version", response.content)

    def test_change_status_button_user_has_edit_perm(self):
        """Invalidate button appears when the user has edit permission and the instance is valid."""
        user = User.objects.create_user(username="test_edit", password="test_edit")
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_update_button", response.context_data)
        self.assertTrue(response.context_data["show_update_button"])
        self.assertContains(
            response,
            reverse(
                "cdsa:signed_agreements:members:update",
                args=[self.obj.signed_agreement.cc_id],
            ),
        )

    def test_change_status_button_user_has_view_perm(self):
        """Invalidate button does not appear when the user has view permission and the instance is valid."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_update_button", response.context_data)
        self.assertFalse(response.context_data["show_update_button"])
        self.assertNotContains(
            response,
            reverse(
                "cdsa:signed_agreements:members:update",
                args=[self.obj.signed_agreement.cc_id],
            ),
        )


class MemberAgreementListTest(TestCase):
    """Tests for the MemberAgreementList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:members:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.MemberAgreementList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(
            response.context_data["table"], tables.MemberAgreementTable
        )

    def test_workspace_table_none(self):
        """No rows are shown if there are no MemberAgreement objects."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_workspace_table_three(self):
        """Two rows are shown if there are three MemberAgreement objects."""
        factories.MemberAgreementFactory.create_batch(3)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 3)


class DataAffiliateAgreementCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for the DataAffiliateAgreementCreate view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        # Create the admins group.
        self.cc_admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:data_affiliates:new", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.DataAffiliateAgreementCreate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has only view permission."""
        user_view_perm = User.objects.create_user(
            username="test-none", password="test-none"
        )
        user_view_perm.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url())
        request.user = user_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_has_forms_in_context(self):
        """Response includes a form."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertTrue("form" in response.context_data)
        self.assertTrue("formset" in response.context_data)

    def test_form_classes(self):
        """Form is the expected class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIsInstance(response.context_data["form"], forms.SignedAgreementForm)
        self.assertIsInstance(
            response.context_data["formset"].forms[0], forms.DataAffiliateAgreementForm
        )

    def test_can_create_object(self):
        """Can create an object."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        # API response to create the associated anvil_access_group.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234",
            status=201,
            json={"message": "mock message"},
        )
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234",
            status=201,
            json={"message": "mock message"},
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # New objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 1)
        new_agreement = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(new_agreement.cc_id, 1234)
        self.assertEqual(new_agreement.representative, representative)
        self.assertEqual(new_agreement.representative_role, "Test role")
        self.assertEqual(new_agreement.signing_institution, "Test institution")
        self.assertEqual(new_agreement.date_signed, date.fromisoformat("2023-01-01"))
        self.assertEqual(new_agreement.is_primary, True)
        # Type was set correctly.
        self.assertEqual(new_agreement.type, new_agreement.DATA_AFFILIATE)
        # AnVIL group was set correctly.
        self.assertIsInstance(new_agreement.anvil_access_group, ManagedGroup)
        self.assertEqual(
            new_agreement.anvil_access_group.name, "TEST_PRIMED_CDSA_ACCESS_1234"
        )
        self.assertEqual(
            new_agreement.status, models.SignedAgreement.StatusChoices.ACTIVE
        )
        # Check the agreement type.
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 1)
        new_agreement_type = models.DataAffiliateAgreement.objects.latest("pk")
        self.assertEqual(new_agreement.dataaffiliateagreement, new_agreement_type)
        self.assertEqual(new_agreement_type.study, study)
        self.assertIsInstance(new_agreement_type.anvil_upload_group, ManagedGroup)
        self.assertEqual(
            new_agreement_type.anvil_upload_group.name, "TEST_PRIMED_CDSA_UPLOAD_1234"
        )

    def test_redirect_url(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        # API response to create the associated anvil_access_group.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234",
            status=201,
            json={"message": "mock message"},
        )
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234",
            status=201,
            json={"message": "mock message"},
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertRedirects(response, new_object.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        # API response to create the associated anvil_access_group.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234",
            status=201,
            json={"message": "mock message"},
        )
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234",
            status=201,
            json={"message": "mock message"},
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.DataAffiliateAgreementCreate.success_message, str(messages[0])
        )

    def test_error_missing_cc_id(self):
        """Form shows an error when cc_id is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                # "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("required", form.errors["cc_id"][0])

    def test_invalid_cc_id(self):
        """Form shows an error when cc_id is invalid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": -1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)

    def test_error_missing_representative(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                # "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative", form.errors)
        self.assertEqual(len(form.errors["representative"]), 1)
        self.assertIn("required", form.errors["representative"][0])

    def test_error_invalid_representative(self):
        """Form shows an error when representative is invalid."""
        self.client.force_login(self.user)
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": 9999,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative", form.errors)
        self.assertEqual(len(form.errors["representative"]), 1)
        self.assertIn("valid", form.errors["representative"][0])

    def test_error_missing_representative_role(self):
        """Form shows an error when representative_role is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                # "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative_role", form.errors)
        self.assertEqual(len(form.errors["representative_role"]), 1)
        self.assertIn("required", form.errors["representative_role"][0])

    def test_error_missing_signing_institution(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                # "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("signing_institution", form.errors)
        self.assertEqual(len(form.errors["signing_institution"]), 1)
        self.assertIn("required", form.errors["signing_institution"][0])

    def test_error_missing_version(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                # "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("required", form.errors["version"][0])

    def test_error_invalid_version(self):
        """Form shows an error when version is invalid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": 9999,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("valid", form.errors["version"][0])

    def test_error_missing_date_signed(self):
        """Form shows an error when date_signed is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                # "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("date_signed", form.errors)
        self.assertEqual(len(form.errors["date_signed"]), 1)
        self.assertIn("required", form.errors["date_signed"][0])

    def test_error_missing_is_primary(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                # "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("is_primary", form.errors)
        self.assertEqual(len(form.errors["is_primary"]), 1)
        self.assertIn("required", form.errors["is_primary"][0])

    def test_error_missing_study(self):
        """Form shows an error when study is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                # "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertTrue(form.is_valid())
        formset = response.context_data["formset"]
        self.assertFalse(formset.is_valid())
        self.assertFalse(formset.forms[0].is_valid())
        self.assertEqual(len(formset.forms[0].errors), 1)
        self.assertIn("study", formset.forms[0].errors)
        self.assertEqual(len(formset.forms[0].errors["study"]), 1)
        self.assertIn("required", formset.forms[0].errors["study"][0])

    def test_error_invalid_memberagreement_study_site(self):
        """Form shows an error when study_site is invalid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": 999,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        form = response.context_data["form"]
        self.assertTrue(form.is_valid())
        formset = response.context_data["formset"]
        self.assertFalse(formset.is_valid())
        self.assertEqual(len(formset.forms[0].errors), 1)
        self.assertIn("study", formset.forms[0].errors)
        self.assertEqual(len(formset.forms[0].errors["study"]), 1)
        self.assertIn("valid", formset.forms[0].errors["study"][0])

    def test_error_duplicate_project_id(self):
        """Form shows an error when trying to create a duplicate dbgap_phs."""
        obj = factories.DataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": obj.signed_agreement.cc_id,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(
            models.SignedAgreement.objects.count(), 1
        )  # One already existed.
        self.assertEqual(
            models.DataAffiliateAgreement.objects.count(), 1
        )  # One already existed.
        # Form has errors in the correct field.
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("already exists", form.errors["cc_id"][0])

    def test_post_blank_data(self):
        """Posting blank data does not create an object."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {})
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())

    def test_creates_anvil_groups(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345",
            status=201,
            json={"message": "mock message"},
        )
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_2345",
            status=201,
            json={"message": "mock message"},
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_2345/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        # An access group was created.
        self.assertEqual(
            new_object.anvil_access_group.name, "TEST_PRIMED_CDSA_ACCESS_2345"
        )
        self.assertTrue(new_object.anvil_access_group.is_managed_by_app)
        # An upload group was created.
        self.assertEqual(
            new_object.dataaffiliateagreement.anvil_upload_group.name,
            "TEST_PRIMED_CDSA_UPLOAD_2345",
        )
        self.assertTrue(
            new_object.dataaffiliateagreement.anvil_upload_group.is_managed_by_app
        )
        # Group-group memberships was created with PRIMED_CC_ADMINS as an admin of the access/uploader group.
        new_membership_1 = GroupGroupMembership.objects.get(
            parent_group=new_object.anvil_access_group, child_group=self.cc_admins_group
        )
        self.assertEqual(new_membership_1.role, GroupGroupMembership.ADMIN)
        new_membership_2 = GroupGroupMembership.objects.get(
            parent_group=new_object.dataaffiliateagreement.anvil_upload_group,
            child_group=self.cc_admins_group,
        )
        self.assertEqual(new_membership_2.role, GroupGroupMembership.ADMIN)

    @override_settings(ANVIL_DATA_ACCESS_GROUP_PREFIX="foo")
    def test_creates_anvil_access_group_different_setting(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/foo_CDSA_ACCESS_2345",
            status=201,
            json={"message": "mock message"},
        )
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/foo_CDSA_UPLOAD_2345",
            status=201,
            json={"message": "mock message"},
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/foo_CDSA_ACCESS_2345/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/foo_CDSA_UPLOAD_2345/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(ManagedGroup.objects.count(), 3)
        # A new group was created.
        self.assertEqual(new_object.anvil_access_group.name, "foo_CDSA_ACCESS_2345")
        self.assertTrue(new_object.anvil_access_group.is_managed_by_app)
        # An upload group was created.
        self.assertEqual(
            new_object.dataaffiliateagreement.anvil_upload_group.name,
            "foo_CDSA_UPLOAD_2345",
        )
        self.assertTrue(
            new_object.dataaffiliateagreement.anvil_upload_group.is_managed_by_app
        )

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foo")
    def test_creates_anvil_groups_different_setting_cc_admins_group_name(self):
        """View creates a managed group upon when form is valid."""
        admin_group = ManagedGroup.objects.create(name="foo", email="foo@firecloud.org")
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345",
            status=201,
            json={"message": "mock message"},
        )
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_2345",
            status=201,
            json={"message": "mock message"},
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345/admin/foo@firecloud.org",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_2345/admin/foo@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        membership_1 = GroupGroupMembership.objects.get(
            parent_group=new_object.anvil_access_group,
            child_group=admin_group,
        )
        self.assertEqual(membership_1.role, GroupGroupMembership.ADMIN)
        membership_2 = GroupGroupMembership.objects.get(
            parent_group=new_object.dataaffiliateagreement.anvil_upload_group,
            child_group=admin_group,
        )
        self.assertEqual(membership_2.role, GroupGroupMembership.ADMIN)

    def test_access_group_create_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating the group."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        # API response to create the associated anvil_access_group.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1",
            status=500,
            json={"message": "other error"},
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        formset = response.context["formset"]
        self.assertTrue(formset.is_valid())
        # ...but there was some error from the API.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual("AnVIL API Error: other error", str(messages[0]))
        # No objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        self.assertEqual(ManagedGroup.objects.count(), 1)  # Just the admins group.

    def test_upload_group_create_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating the group."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        # API response to create the associated anvil_access_group.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1",
            status=201,
            json={"message": "mock message"},
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1",
            status=500,
            json={"message": "other error"},
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        formset = response.context["formset"]
        self.assertTrue(formset.is_valid())
        # ...but there was some error from the API.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual("AnVIL API Error: other error", str(messages[0]))
        # No objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        self.assertEqual(ManagedGroup.objects.count(), 1)  # Just the admins group.

    def test_access_group_already_exists_in_app(self):
        """No objects are created if the managed group already exists in the app."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        # Create a group with the same name.
        ManagedGroupFactory.create(name="TEST_PRIMED_CDSA_ACCESS_1")
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        # ...but there was an error with the group name.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.DataAffiliateAgreementCreate.ERROR_CREATING_GROUP, str(messages[0])
        )
        self.assertEqual(models.SignedAgreement.objects.count(), 0)

    def test_upload_group_already_exists_in_app(self):
        """No objects are created if the managed group already exists in the app."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        # Create a group with the same name.
        ManagedGroupFactory.create(name="TEST_PRIMED_CDSA_UPLOAD_1")
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        # ...but there was an error with the group name.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.DataAffiliateAgreementCreate.ERROR_CREATING_GROUP, str(messages[0])
        )
        self.assertEqual(models.SignedAgreement.objects.count(), 0)

    def test_admin_group_membership_access_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating admin group membership."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        # API response to create the associated anvil_access_group.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234",
            status=201,
            json={"message": "mock message"},
        )
        # self.anvil_response_mock.add(
        #     responses.POST,
        #     self.api_client.sam_entry_point
        #     + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234",
        #     status=201,
        #     json={"message": "mock message"},
        # )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=400,
        )
        # self.anvil_response_mock.add(
        #     responses.PUT,
        #     self.api_client.sam_entry_point
        #     + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
        #     status=204,
        # )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        formset = response.context["formset"]
        self.assertTrue(formset.is_valid())
        # ...but there was some error from the API.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual("AnVIL API Error: other error", str(messages[0]))
        # No objects were created.
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        self.assertEqual(ManagedGroup.objects.count(), 1)  # Just the admin group.

    def test_admin_group_membership_upload_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating admin group membership."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        # API response to create the associated anvil_access_group.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234",
            status=201,
            json={"message": "mock message"},
        )
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234",
            status=201,
            json={"message": "mock message"},
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_UPLOAD_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=404,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        formset = response.context["formset"]
        self.assertTrue(formset.is_valid())
        # ...but there was some error from the API.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual("AnVIL API Error: other error", str(messages[0]))
        # No objects were created.
        self.assertEqual(models.DataAffiliateAgreement.objects.count(), 0)
        self.assertEqual(ManagedGroup.objects.count(), 1)  # Just the admin group.


class DataAffiliateAgreementDetailTest(TestCase):
    """Tests for the DataAffiliateAgreement view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        # Create an object test this with.
        self.obj = factories.DataAffiliateAgreementFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:data_affiliates:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.DataAffiliateAgreementDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, cc_id=1)

    def test_view_status_code_with_existing_object(self):
        """Returns a successful status code for an existing object pk."""
        # Only clients load the template.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)

    def test_view_status_code_with_invalid_pk(self):
        """Raises a 404 error with an invalid object pk."""
        request = self.factory.get(self.get_url(self.obj.signed_agreement.cc_id + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, pk=self.obj.signed_agreement.cc_id + 1)

    def test_response_includes_link_to_user_profile(self):
        """Response includes a link to the user profile page."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertContains(
            response, self.obj.signed_agreement.representative.get_absolute_url()
        )

    def test_response_includes_link_to_study(self):
        """Response includes a link to the study detail page."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertContains(response, self.obj.study.get_absolute_url())

    def test_response_includes_link_to_anvil_access_group(self):
        """Response includes a link to the AnVIL access group detail page."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertContains(
            response, self.obj.signed_agreement.anvil_access_group.get_absolute_url()
        )

    def test_response_includes_link_to_anvil_upload_group(self):
        """Response includes a link to the AnVIL access group detail page."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertContains(response, self.obj.anvil_upload_group.get_absolute_url())

    def test_response_show_deprecation_message_valid(self):
        """response context does not show a deprecation warning when AgreementMajorVersion is valid."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertFalse(response.context_data["show_deprecation_message"])
        self.assertNotIn(b"Deprecated CDSA version", response.content)

    def test_response_show_deprecation_message_not_valid(self):
        """response context does show a deprecation warning when AgreementMajorVersion is not valid."""
        self.obj.signed_agreement.version.major_version.is_valid = False
        self.obj.signed_agreement.version.major_version.save()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertTrue(response.context_data["show_deprecation_message"])
        self.assertIn(b"Deprecated CDSA version", response.content)

    def test_change_status_button_user_has_edit_perm(self):
        """Invalidate button appears when the user has edit permission and the instance is valid."""
        user = User.objects.create_user(username="test_edit", password="test_edit")
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_update_button", response.context_data)
        self.assertTrue(response.context_data["show_update_button"])
        self.assertContains(
            response,
            reverse(
                "cdsa:signed_agreements:data_affiliates:update",
                args=[self.obj.signed_agreement.cc_id],
            ),
        )

    def test_change_status_button_user_has_view_perm(self):
        """Invalidate button does not appear when the user has view permission and the instance is valid."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_update_button", response.context_data)
        self.assertFalse(response.context_data["show_update_button"])
        self.assertNotContains(
            response,
            reverse(
                "cdsa:signed_agreements:data_affiliates:update",
                args=[self.obj.signed_agreement.cc_id],
            ),
        )


class DataAffiliateAgreementListTest(TestCase):
    """Tests for the DataAffiliateAgreement view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:data_affiliates:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.DataAffiliateAgreementList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(
            response.context_data["table"], tables.DataAffiliateAgreementTable
        )

    def test_workspace_table_none(self):
        """No rows are shown if there are no DataAffiliateAgreement objects."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_workspace_table_three(self):
        """Two rows are shown if there are three DataAffiliateAgreement objects."""
        factories.DataAffiliateAgreementFactory.create_batch(3)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 3)


class NonDataAffiliateAgreementCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for the DataAffiliateAgreementCreate view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        # Create the admins group.
        self.cc_admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:non_data_affiliates:new", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.NonDataAffiliateAgreementCreate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has only view permission."""
        user_view_perm = User.objects.create_user(
            username="test-none", password="test-none"
        )
        user_view_perm.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url())
        request.user = user_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_has_forms_in_context(self):
        """Response includes a form."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertTrue("form" in response.context_data)
        self.assertTrue("formset" in response.context_data)

    def test_form_classes(self):
        """Form is the expected class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIsInstance(response.context_data["form"], forms.SignedAgreementForm)
        self.assertIsInstance(
            response.context_data["formset"].forms[0],
            forms.NonDataAffiliateAgreementForm,
        )

    def test_can_create_object(self):
        """Can create an object."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        # API response to create the associated anvil_access_group.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234",
            status=201,
            json={"message": "mock message"},
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 302)
        # New objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 1)
        new_agreement = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(new_agreement.cc_id, 1234)
        self.assertEqual(new_agreement.representative, representative)
        self.assertEqual(new_agreement.representative_role, "Test role")
        self.assertEqual(new_agreement.signing_institution, "Test institution")
        self.assertEqual(new_agreement.date_signed, date.fromisoformat("2023-01-01"))
        self.assertEqual(new_agreement.is_primary, True)
        # Type was set correctly.
        self.assertEqual(new_agreement.type, new_agreement.NON_DATA_AFFILIATE)
        # AnVIL group was set correctly.
        self.assertIsInstance(new_agreement.anvil_access_group, ManagedGroup)
        self.assertEqual(
            new_agreement.anvil_access_group.name, "TEST_PRIMED_CDSA_ACCESS_1234"
        )
        self.assertEqual(
            new_agreement.status, models.SignedAgreement.StatusChoices.ACTIVE
        )
        # Check the agreement type.
        self.assertEqual(models.NonDataAffiliateAgreement.objects.count(), 1)
        new_agreement_type = models.NonDataAffiliateAgreement.objects.latest("pk")
        self.assertEqual(new_agreement.nondataaffiliateagreement, new_agreement_type)
        self.assertEqual(new_agreement_type.affiliation, "Foo Bar")

    def test_redirect_url(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertRedirects(response, new_object.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1234/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.NonDataAffiliateAgreementCreate.success_message, str(messages[0])
        )

    def test_error_missing_cc_id(self):
        """Form shows an error when cc_id is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                # "cc_id": 1234,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("required", form.errors["cc_id"][0])

    def test_invalid_cc_id(self):
        """Form shows an error when cc_id is invalid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": -1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)

    def test_error_missing_representative(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                # "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative", form.errors)
        self.assertEqual(len(form.errors["representative"]), 1)
        self.assertIn("required", form.errors["representative"][0])

    def test_error_invalid_representative(self):
        """Form shows an error when representative is invalid."""
        self.client.force_login(self.user)
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": 9999,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative", form.errors)
        self.assertEqual(len(form.errors["representative"]), 1)
        self.assertIn("valid", form.errors["representative"][0])

    def test_error_missing_representative_role(self):
        """Form shows an error when representative_role is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                # "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative_role", form.errors)
        self.assertEqual(len(form.errors["representative_role"]), 1)
        self.assertIn("required", form.errors["representative_role"][0])

    def test_error_missing_signing_institution(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                # "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("signing_institution", form.errors)
        self.assertEqual(len(form.errors["signing_institution"]), 1)
        self.assertIn("required", form.errors["signing_institution"][0])

    def test_error_missing_version(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                # "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("required", form.errors["version"][0])

    def test_error_invalid_version(self):
        """Form shows an error when version is invalid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": 999,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("valid", form.errors["version"][0])

    def test_error_missing_date_signed(self):
        """Form shows an error when date_signed is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                # "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("date_signed", form.errors)
        self.assertEqual(len(form.errors["date_signed"]), 1)
        self.assertIn("required", form.errors["date_signed"][0])

    def test_error_missing_is_primary(self):
        """Form shows an error when representative is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                # "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("is_primary", form.errors)
        self.assertEqual(len(form.errors["is_primary"]), 1)
        self.assertIn("required", form.errors["is_primary"][0])

    def test_error_missing_nondataaffiliateagreement_affiliation(self):
        """Form shows an error when study_site is missing."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                # "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.MemberAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertTrue(form.is_valid())
        formset = response.context_data["formset"]
        self.assertFalse(formset.is_valid())
        self.assertFalse(formset.forms[0].is_valid())
        self.assertEqual(len(formset.forms[0].errors), 1)
        self.assertIn("affiliation", formset.forms[0].errors)
        self.assertEqual(len(formset.forms[0].errors["affiliation"]), 1)
        self.assertIn("required", formset.forms[0].errors["affiliation"][0])

    def test_error_duplicate_project_id(self):
        """Form shows an error when trying to create a duplicate dbgap_phs."""
        obj = factories.NonDataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": obj.signed_agreement.cc_id,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(
            models.SignedAgreement.objects.count(), 1
        )  # One already existed.
        self.assertEqual(
            models.NonDataAffiliateAgreement.objects.count(), 1
        )  # One already existed.
        # Form has errors in the correct field.
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("already exists", form.errors["cc_id"][0])

    def test_error_is_primary_false(self):
        """Form shows an error when trying to create a duplicate dbgap_phs."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": False,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.NonDataAffiliateAgreement.objects.count(), 0)
        # Form has errors in the correct field.
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn(NON_FIELD_ERRORS, form.errors)
        self.assertEqual(len(form.errors[NON_FIELD_ERRORS]), 1)
        self.assertIn("primary", form.errors[NON_FIELD_ERRORS][0])

    def test_post_blank_data(self):
        """Posting blank data does not create an object."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {})
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())

    def test_creates_anvil_access_group(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(ManagedGroup.objects.count(), 2)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "TEST_PRIMED_CDSA_ACCESS_2345")
        self.assertTrue(new_group.is_managed_by_app)
        # A group-group membership was created with PRIMED_CC_ADMINS as an admin of the access group.
        new_membership = GroupGroupMembership.objects.get(
            parent_group=new_object.anvil_access_group, child_group=self.cc_admins_group
        )
        self.assertEqual(new_membership.role, GroupGroupMembership.ADMIN)

    @override_settings(ANVIL_DATA_ACCESS_GROUP_PREFIX="foo")
    def test_creates_anvil_groups_different_setting(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        api_url = (
            self.api_client.sam_entry_point + "/api/groups/v1/foo_CDSA_ACCESS_2345"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/foo_CDSA_ACCESS_2345/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(ManagedGroup.objects.count(), 2)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "foo_CDSA_ACCESS_2345")
        self.assertTrue(new_group.is_managed_by_app)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foo")
    def test_creates_anvil_groups_different_setting_cc_admins_group_name(self):
        """View creates a managed group upon when form is valid."""
        admin_group = ManagedGroupFactory.create(name="foo", email="foo@firecloud.org")
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_2345/admin/foo@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 2345,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        membership = GroupGroupMembership.objects.get(
            parent_group=new_object.anvil_access_group,
            child_group=admin_group,
        )
        self.assertEqual(membership.role, GroupGroupMembership.ADMIN)

    def test_manage_group_create_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating the group."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = (
            self.api_client.sam_entry_point + "/api/groups/v1/TEST_PRIMED_CDSA_ACCESS_1"
        )
        self.anvil_response_mock.add(
            responses.POST, api_url, status=500, json={"message": "other error"}
        )
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        formset = response.context["formset"]
        self.assertTrue(formset.is_valid())
        # ...but there was some error from the API.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual("AnVIL API Error: other error", str(messages[0]))
        # No objects were created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)
        self.assertEqual(models.NonDataAffiliateAgreement.objects.count(), 0)
        self.assertEqual(ManagedGroup.objects.count(), 1)  # Just the admins group.

    def test_managed_group_already_exists_in_app(self):
        """No objects are created if the managed group already exists in the app."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        # Create a group with the same name.
        ManagedGroupFactory.create(name="TEST_PRIMED_CDSA_ACCESS_1")
        response = self.client.post(
            self.get_url(),
            {
                "cc_id": 1,
                "representative": representative.pk,
                "representative_role": "Test role",
                "signing_institution": "Test institution",
                "version": agreement_version.pk,
                "date_signed": "2023-01-01",
                "is_primary": True,
                "agreementtype-TOTAL_FORMS": 1,
                "agreementtype-INITIAL_FORMS": 0,
                "agreementtype-MIN_NUM_FORMS": 1,
                "agreementtype-MAX_NUM_FORMS": 1,
                "agreementtype-0-affiliation": "Foo Bar",
            },
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        # ...but there was an error with the group name.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.NonDataAffiliateAgreementCreate.ERROR_CREATING_GROUP, str(messages[0])
        )
        # No dbGaPApplication was created.
        self.assertEqual(models.SignedAgreement.objects.count(), 0)


class NonDataAffiliateAgreementDetailTest(TestCase):
    """Tests for the NonDataAffiliateAgreement view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        # Create an object test this with.
        self.obj = factories.NonDataAffiliateAgreementFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:non_data_affiliates:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.NonDataAffiliateAgreementDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, cc_id=1)

    def test_view_status_code_with_existing_object(self):
        """Returns a successful status code for an existing object pk."""
        # Only clients load the template.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)

    def test_view_status_code_with_invalid_pk(self):
        """Raises a 404 error with an invalid object pk."""
        request = self.factory.get(self.get_url(self.obj.signed_agreement.cc_id + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, pk=self.obj.signed_agreement.cc_id + 1)

    def test_response_includes_link_to_user_profile(self):
        """Response includes a link to the user profile page."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertContains(
            response, self.obj.signed_agreement.representative.get_absolute_url()
        )

    def test_response_includes_link_to_anvil_access_group(self):
        """Response includes a link to the AnVIL access group detail page."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertContains(
            response, self.obj.signed_agreement.anvil_access_group.get_absolute_url()
        )

    def test_response_show_deprecation_message_valid(self):
        """response context does not show a deprecation warning when AgreementMajorVersion is valid."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertFalse(response.context_data["show_deprecation_message"])
        self.assertNotIn(b"Deprecated CDSA version", response.content)

    def test_response_show_deprecation_message_is_not_valid(self):
        """response context does show a deprecation warning when AgreementMajorVersion is not valid."""
        self.obj.signed_agreement.version.major_version.is_valid = False
        self.obj.signed_agreement.version.major_version.save()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_deprecation_message", response.context_data)
        self.assertTrue(response.context_data["show_deprecation_message"])
        self.assertIn(b"Deprecated CDSA version", response.content)

    def test_change_status_button_user_has_edit_perm(self):
        """Invalidate button appears when the user has edit permission and the instance is valid."""
        user = User.objects.create_user(username="test_edit", password="test_edit")
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_update_button", response.context_data)
        self.assertTrue(response.context_data["show_update_button"])
        self.assertContains(
            response,
            reverse(
                "cdsa:signed_agreements:non_data_affiliates:update",
                args=[self.obj.signed_agreement.cc_id],
            ),
        )

    def test_change_status_button_user_has_view_perm(self):
        """Invalidate button does not appear when the user has view permission and the instance is valid."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.signed_agreement.cc_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn("show_update_button", response.context_data)
        self.assertFalse(response.context_data["show_update_button"])
        self.assertNotContains(
            response,
            reverse(
                "cdsa:signed_agreements:non_data_affiliates:update",
                args=[self.obj.signed_agreement.cc_id],
            ),
        )


class NonDataAffiliateAgreementListTest(TestCase):
    """Tests for the NonDataAffiliateAgreement view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:signed_agreements:non_data_affiliates:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.NonDataAffiliateAgreementList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(
            response.context_data["table"], tables.NonDataAffiliateAgreementTable
        )

    def test_workspace_table_none(self):
        """No rows are shown if there are no NonDataAffiliateAgreement objects."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_workspace_table_three(self):
        """Two rows are shown if there are three NonDataAffiliateAgreement objects."""
        factories.NonDataAffiliateAgreementFactory.create_batch(3)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 3)


class RecordsIndexTest(TestCase):
    """Tests for the RecordsIndex view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:records:index", args=args)

    def test_status_code_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_status_code_user_logged_in(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_links(self):
        """response includes the correct links."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertContains(response, reverse("cdsa:records:representatives"))
        self.assertContains(response, reverse("cdsa:records:studies"))
        self.assertContains(response, reverse("cdsa:records:user_access"))
        self.assertContains(response, reverse("cdsa:records:workspaces"))


class RepresentativeRecordsList(TestCase):
    """Tests for the RepresentativeRecordsList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:records:representatives", args=args)

    def test_status_code_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_status_code_user_logged_in(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(
            response.context_data["table"], tables.RepresentativeRecordsTable
        )

    def test_table_no_rows(self):
        """No rows are shown if there are no SignedAgreement objects."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_table_three_rows(self):
        """Three rows are shown if there are three SignedAgreement objects."""
        factories.MemberAgreementFactory.create()
        factories.DataAffiliateAgreementFactory.create()
        factories.NonDataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 3)

    def test_only_includes_active_agreements(self):
        active_agreement = factories.MemberAgreementFactory.create()
        lapsed_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.LAPSED
        )
        withdrawn_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        replaced_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.REPLACED
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(active_agreement.signed_agreement, table.data)
        self.assertNotIn(lapsed_agreement.signed_agreement, table.data)
        self.assertNotIn(withdrawn_agreement.signed_agreement, table.data)
        self.assertNotIn(replaced_agreement.signed_agreement, table.data)


class SignedAgreementAuditTest(TestCase):
    """Tests for the SignedAgreementAudit view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        # Create the test group.
        self.anvil_cdsa_group = ManagedGroupFactory.create(name="TEST_PRIMED_CDSA")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "cdsa:audit:signed_agreements:all",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.SignedAgreementAudit.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission_view(self):
        """Returns successful response code if the user has view permission."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_context_data_access_audit(self):
        """The data_access_audit exists in the context."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("audit", response.context_data)
        self.assertIsInstance(
            response.context_data["audit"],
            signed_agreement_audit.SignedAgreementAccessAudit,
        )
        self.assertTrue(response.context_data["audit"].completed)

    def test_context_verified_table_access(self):
        """verified_table shows a record when audit has verified access."""
        member_agreement = factories.MemberAgreementFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            signed_agreement_audit.SignedAgreementAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("signed_agreement"),
            member_agreement.signed_agreement,
        )
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            signed_agreement_audit.SignedAgreementAccessAudit.ACTIVE_PRIMARY_AGREEMENT,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_verified_table_no_access(self):
        """verified_table shows a record when audit has verified no access."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            signed_agreement_audit.SignedAgreementAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("signed_agreement"),
            member_agreement.signed_agreement,
        )
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            signed_agreement_audit.SignedAgreementAccessAudit.INACTIVE_AGREEMENT,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_needs_action_table_grant(self):
        """needs_action_table shows a record when audit finds that access needs to be granted."""
        member_agreement = factories.MemberAgreementFactory.create()
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            signed_agreement_audit.SignedAgreementAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("signed_agreement"),
            member_agreement.signed_agreement,
        )
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            signed_agreement_audit.SignedAgreementAccessAudit.ACTIVE_PRIMARY_AGREEMENT,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_error_table_has_access(self):
        """error shows a record when audit finds that access needs to be removed."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        GroupGroupMembershipFactory.create(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("errors_table", response.context_data)
        table = response.context_data["errors_table"]
        self.assertIsInstance(
            table,
            signed_agreement_audit.SignedAgreementAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("signed_agreement"),
            member_agreement.signed_agreement,
        )
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            signed_agreement_audit.SignedAgreementAccessAudit.NO_PRIMARY_AGREEMENT,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    @override_settings(ANVIL_CDSA_GROUP_NAME="FOOBAR")
    def test_anvil_cdsa_group_does_not_exist(self):
        """The view redirects with a message if the CDSA group does not exist in the app."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertRedirects(response, reverse("anvil_consortium_manager:index"))
        # Check messages.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertIn("FOOBAR", str(messages[0]))
        self.assertIn("does not exist", str(messages[0]))


class SignedAgreementAuditResolveTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for the SignedAgreementAuditResolve view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        # Create the test group.
        self.anvil_cdsa_group = ManagedGroupFactory.create(name="TEST_PRIMED_CDSA")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:audit:signed_agreements:resolve", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.SignedAgreementAuditResolve.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1),
        )

    def test_status_code_with_user_permission_view(self):
        """Returns forbidden response code if the user only has view permission."""
        user_view = User.objects.create_user(username="test-view", password="test-view")
        user_view.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_view
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_signed_agreement_does_not_exist(self):
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(1))
        self.assertEqual(response.status_code, 404)

    def test_get_context_data_access_audit(self):
        """The data_access_audit exists in the context."""
        member_agreement = factories.MemberAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(member_agreement.signed_agreement.cc_id)
        )
        self.assertIn("audit_result", response.context_data)
        self.assertIsInstance(
            response.context_data["audit_result"],
            signed_agreement_audit.AccessAuditResult,
        )

    def test_get_context_verified_access(self):
        """Context with VerifiedAccess."""
        member_agreement = factories.MemberAgreementFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        # Check the audit_result in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(member_agreement.signed_agreement.cc_id)
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, signed_agreement_audit.VerifiedAccess)
        self.assertContains(response, audit_result.note)
        self.assertContains(response, "No action needed")

    def test_get_context_verified_no_access(self):
        """Context with VerifiedNoAccess."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.anvil_cdsa_group,
        #     child_group=member_agreement.signed_agreement.anvil_access_group,
        # )
        # Check the audit_result in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(member_agreement.signed_agreement.cc_id)
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, signed_agreement_audit.VerifiedNoAccess)
        self.assertContains(response, audit_result.note)
        self.assertContains(response, "No action needed")

    def test_get_context_remove_access(self):
        """Context with RemoveAccess."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        GroupGroupMembershipFactory.create(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        # Check the audit_result in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(member_agreement.signed_agreement.cc_id)
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, signed_agreement_audit.RemoveAccess)
        self.assertContains(response, audit_result.note)
        self.assertContains(response, audit_result.action)

    def test_get_context_grant_access(self):
        """Context with GrantAccess."""
        member_agreement = factories.MemberAgreementFactory.create()
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.anvil_cdsa_group,
        #     child_group=member_agreement.signed_agreement.anvil_access_group,
        # )
        # Check the audit_result in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(member_agreement.signed_agreement.cc_id)
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, signed_agreement_audit.GrantAccess)
        self.assertContains(response, audit_result.note)
        self.assertContains(response, audit_result.action)

    def test_post_context_verified_access(self):
        """Context with VerifiedAccess."""
        member_agreement = factories.MemberAgreementFactory.create()
        date_created = timezone.now() - timedelta(weeks=3)
        with freeze_time(date_created):
            membership = GroupGroupMembershipFactory.create(
                parent_group=self.anvil_cdsa_group,
                child_group=member_agreement.signed_agreement.anvil_access_group,
            )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}
        )
        self.assertRedirects(response, member_agreement.get_absolute_url())
        # Make sure the membership hasn't changed.
        membership.refresh_from_db()
        self.assertEqual(membership.modified, date_created)

    def test_post_context_verified_no_access(self):
        """Context with VerifiedNoAccess."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.anvil_cdsa_group,
        #     child_group=member_agreement.signed_agreement.anvil_access_group,
        # )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}
        )
        self.assertRedirects(response, member_agreement.get_absolute_url())
        self.assertEqual(GroupGroupMembership.objects.count(), 0)

    def test_post_context_remove_access(self):
        """Context with RemoveAccess."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=204,
        )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}
        )
        self.assertRedirects(response, member_agreement.get_absolute_url())
        # Make sure the membership hasn't changed.
        with self.assertRaises(GroupGroupMembership.DoesNotExist):
            membership.refresh_from_db()

    def test_post_htmx_context_remove_access(self):
        """Context with RemoveAccess."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=204,
        )
        # Check the response.
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}, **header
        )
        self.assertEqual(
            response.content.decode(), views.SignedAgreementAuditResolve.htmx_success
        )
        # Make sure the membership hasn't changed.
        with self.assertRaises(GroupGroupMembership.DoesNotExist):
            membership.refresh_from_db()

    def test_post_context_grant_access(self):
        """Context with GrantAccess."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345
        )
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.anvil_cdsa_group,
        #     child_group=member_agreement.signed_agreement.anvil_access_group,
        # )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=204,
        )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}
        )
        self.assertRedirects(response, member_agreement.get_absolute_url())
        membership = GroupGroupMembership.objects.get(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        self.assertEqual(membership.role, membership.MEMBER)

    def test_post_htmx_grant_access(self):
        """Context with GrantAccess."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345
        )
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.anvil_cdsa_group,
        #     child_group=member_agreement.signed_agreement.anvil_access_group,
        # )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=204,
        )
        # Check the response.
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}, **header
        )
        self.assertEqual(
            response.content.decode(), views.SignedAgreementAuditResolve.htmx_success
        )
        membership = GroupGroupMembership.objects.get(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        self.assertEqual(membership.role, membership.MEMBER)

    def test_get_only_this_signed_agreement(self):
        """Only runs on the specified signed_agreement."""
        factories.MemberAgreementFactory.create(signed_agreement__cc_id=1234)
        member_agreement = factories.MemberAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(member_agreement.signed_agreement.cc_id)
        )
        self.assertIn("audit_result", response.context_data)
        self.assertIsInstance(
            response.context_data["audit_result"],
            signed_agreement_audit.AccessAuditResult,
        )
        self.assertEqual(
            response.context_data["audit_result"].signed_agreement,
            member_agreement.signed_agreement,
        )

    def test_post_only_this_signed_agreement(self):
        """Only runs on the specified signed_agreement."""
        factories.MemberAgreementFactory.create(signed_agreement__cc_id=1234)
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345
        )
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.anvil_cdsa_group,
        #     child_group=member_agreement.signed_agreement.anvil_access_group,
        # )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=204,
        )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}
        )
        self.assertRedirects(response, member_agreement.get_absolute_url())
        membership = GroupGroupMembership.objects.get(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        self.assertEqual(membership.role, membership.MEMBER)

    def test_anvil_api_error_grant(self):
        """AnVIL API errors are properly handled."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345
        )
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.anvil_cdsa_group,
        #     child_group=member_agreement.signed_agreement.anvil_access_group,
        # )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}
        )
        self.assertEqual(response.status_code, 200)
        # No group membership was created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)
        # Audit result is still GrantAccess.
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, signed_agreement_audit.GrantAccess)
        # A message was added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertIn("AnVIL API Error", str(messages[0]))

    def test_anvil_api_error_grant_htmx(self):
        """AnVIL API errors are properly handled."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345
        )
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.anvil_cdsa_group,
        #     child_group=member_agreement.signed_agreement.anvil_access_group,
        # )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        # Check the response.
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}, **header
        )
        self.assertEqual(
            response.content.decode(), views.SignedAgreementAuditResolve.htmx_error
        )
        # No group membership was created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)
        # No messages waere added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 0)

    def test_anvil_api_error_remove(self):
        """AnVIL API errors are properly handled."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345,
            signed_agreement__status=models.SignedAgreement.StatusChoices.LAPSED,
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}
        )
        self.assertEqual(response.status_code, 200)
        # The group-group membership still exists.
        membership.refresh_from_db()
        # Audit result is still RemoveAccess.
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, signed_agreement_audit.RemoveAccess)
        # A message was added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertIn("AnVIL API Error", str(messages[0]))

    def test_anvil_api_error_remove_htmx(self):
        """AnVIL API errors are properly handled."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345,
            signed_agreement__status=models.SignedAgreement.StatusChoices.LAPSED,
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=self.anvil_cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_CDSA/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        # Check the response.
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}, **header
        )
        self.assertEqual(
            response.content.decode(), views.SignedAgreementAuditResolve.htmx_error
        )
        # The group-group membership still exists.
        membership.refresh_from_db()
        # No messages was added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 0)

    @override_settings(ANVIL_CDSA_GROUP_NAME="FOOBAR")
    def test_anvil_cdsa_group_does_not_exist(self):
        """Settings file has a different CDSA group name."""
        cdsa_group = ManagedGroupFactory.create(name="FOOBAR")
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__cc_id=2345
        )
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.anvil_cdsa_group,
        #     child_group=member_agreement.signed_agreement.anvil_access_group,
        # )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/FOOBAR/member/TEST_PRIMED_CDSA_ACCESS_2345@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=204,
        )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(member_agreement.signed_agreement.cc_id), {}
        )
        self.assertRedirects(response, member_agreement.get_absolute_url())
        membership = GroupGroupMembership.objects.get(
            parent_group=cdsa_group,
            child_group=member_agreement.signed_agreement.anvil_access_group,
        )
        self.assertEqual(membership.role, membership.MEMBER)


class CDSAWorkspaceAuditTest(TestCase):
    """Tests for the SignedAgreementAudit view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.anvil_cdsa_group = ManagedGroupFactory.create(name="TEST_PRIMED_CDSA")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "cdsa:audit:workspaces:all",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.CDSAWorkspaceAudit.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission_view(self):
        """Returns successful response code if the user has view permission."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_context_data_access_audit(self):
        """The data_access_audit exists in the context."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("audit", response.context_data)
        self.assertIsInstance(
            response.context_data["audit"],
            workspace_audit.WorkspaceAccessAudit,
        )
        self.assertTrue(response.context_data["audit"].completed)

    def test_context_verified_table_access(self):
        """verified_table shows a record when audit has verified access."""
        study = StudyFactory.create()
        agreement = factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            workspace_audit.WorkspaceAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            workspace,
        )
        self.assertEqual(
            table.rows[0].get_cell_value("data_affiliate_agreement"),
            agreement,
        )
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            workspace_audit.WorkspaceAccessAudit.ACTIVE_PRIMARY_AGREEMENT,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_verified_table_no_access(self):
        """verified_table shows a record when audit has verified no access."""
        workspace = factories.CDSAWorkspaceFactory.create()
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            workspace_audit.WorkspaceAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            workspace,
        )
        self.assertIsNone(table.rows[0].get_cell_value("data_affiliate_agreement"))
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            workspace_audit.WorkspaceAccessAudit.NO_PRIMARY_AGREEMENT,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_needs_action_table_grant(self):
        """needs_action_table shows a record when audit finds that access needs to be granted."""
        study = StudyFactory.create()
        agreement = factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            workspace_audit.WorkspaceAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            workspace,
        )
        self.assertEqual(
            table.rows[0].get_cell_value("data_affiliate_agreement"),
            agreement,
        )
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            workspace_audit.WorkspaceAccessAudit.ACTIVE_PRIMARY_AGREEMENT,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_error_table_has_access(self):
        """error shows a record when audit finds that access needs to be removed."""
        workspace = factories.CDSAWorkspaceFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("errors_table", response.context_data)
        table = response.context_data["errors_table"]
        self.assertIsInstance(
            table,
            workspace_audit.WorkspaceAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertIsNone(table.rows[0].get_cell_value("data_affiliate_agreement"))
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            workspace_audit.WorkspaceAccessAudit.NO_PRIMARY_AGREEMENT,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    @override_settings(ANVIL_CDSA_GROUP_NAME="FOOBAR")
    def test_anvil_cdsa_group_does_not_exist(self):
        """The view redirects with a message if the CDSA group does not exist in the app."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertRedirects(response, reverse("anvil_consortium_manager:index"))
        # Check messages.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertIn("FOOBAR", str(messages[0]))
        self.assertIn("does not exist", str(messages[0]))


class CDSAWorkspaceAuditResolveTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for the SignedAgreementAuditResolve view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        # Create the test group.
        self.anvil_cdsa_group = ManagedGroupFactory.create(name="TEST_PRIMED_CDSA")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:audit:workspaces:resolve", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.CDSAWorkspaceAuditResolve.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url("foo", "bar"))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url("foo", "bar"),
        )

    def test_status_code_with_user_permission_view(self):
        """Returns forbidden response code if the user only has view permission."""
        user_view = User.objects.create_user(username="test-view", password="test-view")
        user_view.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url("foo", "bar"))
        request.user = user_view
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url("foo", "bar"))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_billing_project_does_not_exist(self):
        cdsa_workspace = factories.CDSAWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url("foo", cdsa_workspace.workspace.name))
        self.assertEqual(response.status_code, 404)

    def test_workspace_name_does_not_exist(self):
        cdsa_workspace = factories.CDSAWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(cdsa_workspace.workspace.billing_project.name, "foo")
        )
        self.assertEqual(response.status_code, 404)

    def test_get_context_audit_result(self):
        """The data_access_audit exists in the context."""
        workspace = factories.CDSAWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            )
        )
        self.assertIn("audit_result", response.context_data)
        self.assertIsInstance(
            response.context_data["audit_result"],
            workspace_audit.AccessAuditResult,
        )

    def test_get_context_verified_access(self):
        """verified_table shows a record when audit has verified access."""
        study = StudyFactory.create()
        agreement = factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            )
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(
            audit_result,
            workspace_audit.VerifiedAccess,
        )
        self.assertEqual(audit_result.workspace, workspace)
        self.assertEqual(audit_result.data_affiliate_agreement, agreement)
        self.assertEqual(
            audit_result.note,
            workspace_audit.WorkspaceAccessAudit.ACTIVE_PRIMARY_AGREEMENT,
        )
        self.assertIsNone(audit_result.action)

    def test_get_verified_no_access(self):
        """verified_table shows a record when audit has verified no access."""
        workspace = factories.CDSAWorkspaceFactory.create()
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            )
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(
            audit_result,
            workspace_audit.VerifiedNoAccess,
        )
        self.assertEqual(audit_result.workspace, workspace)
        self.assertIsNone(audit_result.data_affiliate_agreement)
        self.assertEqual(
            audit_result.note, workspace_audit.WorkspaceAccessAudit.NO_PRIMARY_AGREEMENT
        )
        self.assertIsNone(audit_result.action)

    def test_get_grant_access(self):
        """needs_action_table shows a record when audit finds that access needs to be granted."""
        study = StudyFactory.create()
        agreement = factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            )
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(
            audit_result,
            workspace_audit.GrantAccess,
        )
        self.assertEqual(audit_result.workspace, workspace)
        self.assertEqual(audit_result.data_affiliate_agreement, agreement)
        self.assertEqual(
            audit_result.note,
            workspace_audit.WorkspaceAccessAudit.ACTIVE_PRIMARY_AGREEMENT,
        )
        self.assertEqual(audit_result.action, "Grant access")

    def test_get_remove_access(self):
        """get request with RemoveAccess audit result."""
        workspace = factories.CDSAWorkspaceFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            )
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, workspace_audit.RemoveAccess)
        self.assertEqual(audit_result.workspace, workspace)
        self.assertIsNone(audit_result.data_affiliate_agreement)
        self.assertEqual(
            audit_result.note, workspace_audit.WorkspaceAccessAudit.NO_PRIMARY_AGREEMENT
        )
        self.assertEqual(audit_result.action, "Remove access")

    def test_post_verified_access(self):
        """Post with VerifiedAccess workspace."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        date_created = timezone.now() - timedelta(weeks=3)
        with freeze_time(date_created):
            membership = GroupGroupMembershipFactory.create(
                parent_group=workspace.workspace.authorization_domains.first(),
                child_group=self.anvil_cdsa_group,
            )
        # Check the response
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
        )
        self.assertRedirects(response, workspace.get_absolute_url())
        # Make sure the membership hasn't changed.
        membership.refresh_from_db()
        self.assertEqual(membership.modified, date_created)
        self.assertEqual(
            membership.parent_group, workspace.workspace.authorization_domains.first()
        )
        self.assertEqual(membership.child_group, self.anvil_cdsa_group)

    def test_post_verified_no_access(self):
        """Post with VerifiedNoAccess workspace."""
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        # membership = GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.anvil_cdsa_group,
        # )
        # Check the response
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
        )
        self.assertRedirects(response, workspace.get_absolute_url())
        self.assertEqual(GroupGroupMembership.objects.count(), 0)

    def test_post_grant_access(self):
        """Context with GrantAccess."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(
            study=study, workspace__name="TEST_CDSA"
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/auth_TEST_CDSA/member/TEST_PRIMED_CDSA@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=204,
        )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
        )
        self.assertRedirects(response, workspace.get_absolute_url())
        membership = GroupGroupMembership.objects.get(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        self.assertEqual(membership.role, membership.MEMBER)

    def test_post_grant_access_htmx(self):
        """Context with GrantAccess."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(
            study=study, workspace__name="TEST_CDSA"
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/auth_TEST_CDSA/member/TEST_PRIMED_CDSA@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=204,
        )
        # Check the response.
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
            **header
        )
        self.assertEqual(
            response.content.decode(), views.SignedAgreementAuditResolve.htmx_success
        )
        # Membership has been created.
        membership = GroupGroupMembership.objects.get(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        self.assertEqual(membership.role, membership.MEMBER)

    def test_post_remove_access(self):
        """Get request with RemoveAccess audit result."""
        workspace = factories.CDSAWorkspaceFactory.create(
            workspace__name="TEST_WORKSPACE"
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/auth_TEST_WORKSPACE/member/TEST_PRIMED_CDSA@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=204,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
        )
        self.assertRedirects(response, workspace.get_absolute_url())
        # Make sure the membership has been deleted.
        with self.assertRaises(GroupGroupMembership.DoesNotExist):
            membership.refresh_from_db()

    def test_post_htmx_remove_access_htmx(self):
        """HTMX post request with RemoveAccess audit result."""
        workspace = factories.CDSAWorkspaceFactory.create(
            workspace__name="TEST_WORKSPACE"
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/auth_TEST_WORKSPACE/member/TEST_PRIMED_CDSA@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=204,
        )
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
            **header
        )
        self.assertEqual(
            response.content.decode(), views.CDSAWorkspaceAuditResolve.htmx_success
        )
        # Make sure the membership has been deleted.
        with self.assertRaises(GroupGroupMembership.DoesNotExist):
            membership.refresh_from_db()

    def test_get_only_this_workspace(self):
        """Only runs on the specified workspace."""
        factories.CDSAWorkspaceFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            )
        )
        self.assertIn("audit_result", response.context_data)
        self.assertIsInstance(
            response.context_data["audit_result"],
            workspace_audit.AccessAuditResult,
        )
        self.assertEqual(response.context_data["audit_result"].workspace, workspace)

    def test_anvil_api_error_grant(self):
        """AnVIL API errors are properly handled."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(
            study=study, workspace__name="TEST_CDSA"
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/auth_TEST_CDSA/member/TEST_PRIMED_CDSA@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
        )
        self.assertEqual(response.status_code, 200)
        # No group membership was created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)
        # Audit result is still GrantAccess.
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, workspace_audit.GrantAccess)
        # A message was added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertIn("AnVIL API Error", str(messages[0]))

    def test_anvil_api_error_grant_htmx(self):
        """AnVIL API errors are properly handled with htmx."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(
            study=study, workspace__name="TEST_CDSA"
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/auth_TEST_CDSA/member/TEST_PRIMED_CDSA@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        # Check the response.
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
            **header
        )
        self.assertEqual(
            response.content.decode(), views.SignedAgreementAuditResolve.htmx_error
        )
        # No group membership was created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)
        # No messages were added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 0)

    def test_anvil_api_error_remove(self):
        """AnVIL API errors are properly handled."""
        workspace = factories.CDSAWorkspaceFactory.create(
            workspace__name="TEST_WORKSPACE"
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/auth_TEST_WORKSPACE/member/TEST_PRIMED_CDSA@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
        )
        self.assertEqual(response.status_code, 200)
        # The group-group membership still exists.
        membership.refresh_from_db()
        # Audit result is still RemoveAccess.
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, workspace_audit.RemoveAccess)
        # A message was added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertIn("AnVIL API Error", str(messages[0]))

    def test_anvil_api_error_remove_htmx(self):
        """AnVIL API errors are properly handled."""
        workspace = factories.CDSAWorkspaceFactory.create(
            workspace__name="TEST_WORKSPACE"
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.anvil_cdsa_group,
        )
        # Add API response
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/auth_TEST_WORKSPACE/member/TEST_PRIMED_CDSA@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
            **header
        )
        self.assertEqual(
            response.content.decode(), views.SignedAgreementAuditResolve.htmx_error
        )
        # The group-group membership still exists.
        membership.refresh_from_db()
        # No messages was added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 0)

    @override_settings(ANVIL_CDSA_GROUP_NAME="FOOBAR")
    def test_different_cdsa_group_name(self):
        """Settings file has a different CDSA group name."""
        cdsa_group = ManagedGroupFactory.create(name="FOOBAR")
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(
            study=study, workspace__name="TEST_CDSA"
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        api_url = (
            self.api_client.sam_entry_point
            + "/api/groups/v1/auth_TEST_CDSA/member/FOOBAR@firecloud.org"
        )
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=204,
        )
        # Check the response.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                workspace.workspace.billing_project.name, workspace.workspace.name
            ),
            {},
        )
        self.assertRedirects(response, workspace.get_absolute_url())
        membership = GroupGroupMembership.objects.get(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=cdsa_group,
        )
        self.assertEqual(membership.role, membership.MEMBER)


class StudyRecordsList(TestCase):
    """Tests for the StudyRecordsList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:records:studies", args=args)

    def test_status_code_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_status_code_user_logged_in(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.StudyRecordsTable)

    def test_table_no_rows(self):
        """No rows are shown if there are no DataAffiliateAgreement objects."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_table_three_rows(self):
        """Three rows are shown if there are three SignedAgreement objects."""
        factories.DataAffiliateAgreementFactory.create_batch(
            3, signed_agreement__is_primary=True
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 3)

    def test_only_shows_data_affiliate_records(self):
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        non_data_affiliate_agreement = (
            factories.NonDataAffiliateAgreementFactory.create(
                signed_agreement__is_primary=True
            )
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(data_affiliate_agreement, table.data)
        self.assertNotIn(member_agreement, table.data)
        self.assertNotIn(non_data_affiliate_agreement, table.data)

    def test_only_shows_primary_data_affiliate_records(self):
        primary_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        component_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(primary_agreement, table.data)
        self.assertNotIn(component_agreement, table.data)

    def test_only_includes_active_agreements(self):
        active_agreement = factories.DataAffiliateAgreementFactory.create()
        lapsed_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.LAPSED
        )
        withdrawn_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        replaced_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.REPLACED
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(active_agreement, table.data)
        self.assertNotIn(lapsed_agreement, table.data)
        self.assertNotIn(withdrawn_agreement, table.data)
        self.assertNotIn(replaced_agreement, table.data)


class UserAccessRecordsList(TestCase):
    """Tests for the StudyRecordsList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:records:user_access", args=args)

    def test_status_code_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_status_code_user_logged_in(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(
            response.context_data["table"], tables.UserAccessRecordsTable
        )

    def test_table_no_rows(self):
        """No rows are shown if there are no users in CDSA access groups."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_table_one_agreement_no_members(self):
        """No row is shown if there is one agreement with no account group members."""
        factories.MemberAgreementFactory.create(signed_agreement__is_primary=True)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_table_one_agreement_one_member(self):
        """One row is shown if there is one agreement and one account group member."""
        agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        GroupAccountMembershipFactory.create(
            group=agreement.signed_agreement.anvil_access_group
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 1)

    def test_table_one_agreements_two_members(self):
        """Two rows are shown if there is one agreement with two account group members."""
        agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        GroupAccountMembershipFactory.create_batch(
            2, group=agreement.signed_agreement.anvil_access_group
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 2)

    def test_table_two_agreements(self):
        """Multiple rows is shown if there are two agreements and multiple account group members."""
        agreement_1 = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        GroupAccountMembershipFactory.create_batch(
            2, group=agreement_1.signed_agreement.anvil_access_group
        )
        agreement_2 = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        GroupAccountMembershipFactory.create_batch(
            3, group=agreement_2.signed_agreement.anvil_access_group
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 5)

    def test_only_shows_records_for_all_agreement_types(self):
        agreement_1 = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        GroupAccountMembershipFactory.create(
            group=agreement_1.signed_agreement.anvil_access_group
        )
        agreement_2 = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        GroupAccountMembershipFactory.create(
            group=agreement_2.signed_agreement.anvil_access_group
        )
        agreement_3 = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        GroupAccountMembershipFactory.create(
            group=agreement_3.signed_agreement.anvil_access_group
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 3)

    def test_shows_includes_component_agreements(self):
        agreement_1 = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        GroupAccountMembershipFactory.create(
            group=agreement_1.signed_agreement.anvil_access_group
        )
        agreement_2 = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        GroupAccountMembershipFactory.create(
            group=agreement_2.signed_agreement.anvil_access_group
        )
        agreement_3 = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        GroupAccountMembershipFactory.create(
            group=agreement_3.signed_agreement.anvil_access_group
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 3)

    def test_does_not_show_anvil_upload_group_members(self):
        agreement = factories.DataAffiliateAgreementFactory.create()
        GroupAccountMembershipFactory.create(group=agreement.anvil_upload_group)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 0)

    def test_does_not_show_other_group_members(self):
        factories.MemberAgreementFactory.create()
        GroupAccountMembershipFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 0)

    def test_only_includes_active_agreements(self):
        active_agreement = factories.MemberAgreementFactory.create()
        active_member = GroupAccountMembershipFactory.create(
            group=active_agreement.signed_agreement.anvil_access_group
        )
        lapsed_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.LAPSED
        )
        lapsed_member = GroupAccountMembershipFactory.create(
            group=lapsed_agreement.signed_agreement.anvil_access_group
        )
        withdrawn_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        withdrawn_member = GroupAccountMembershipFactory.create(
            group=withdrawn_agreement.signed_agreement.anvil_access_group
        )
        replaced_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.REPLACED
        )
        replaced_member = GroupAccountMembershipFactory.create(
            group=replaced_agreement.signed_agreement.anvil_access_group
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(active_member, table.data)
        self.assertNotIn(lapsed_member, table.data)
        self.assertNotIn(withdrawn_member, table.data)
        self.assertNotIn(replaced_member, table.data)


class CDSAWorkspaceRecordsList(TestCase):
    """Tests for the CDSAWorkspaceRecords view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:records:workspaces", args=args)

    def test_status_code_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_status_code_user_logged_in(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(
            response.context_data["table"], tables.CDSAWorkspaceRecordsTable
        )

    def test_table_no_rows(self):
        """No rows are shown if there are no CDSAWorkspaces objects."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_table_two_rows(self):
        """Three rows are shown if there are three CDSAWorkspaces objects."""
        active_workspace_1 = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=active_workspace_1.study)
        active_workspace_2 = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=active_workspace_2.study)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 2)
        self.assertIn(active_workspace_1, table.data)
        self.assertIn(active_workspace_2, table.data)

    def test_only_includes_workspaces_with_active_agreements(self):
        active_workspace = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=active_workspace.study)
        lapsed_workspace = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            study=lapsed_workspace.study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.LAPSED,
        )
        withdrawn_workspace = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            study=withdrawn_workspace.study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        replaced_workspace = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            study=replaced_workspace.study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.REPLACED,
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        table = response.context_data["table"]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(active_workspace, table.data)
        self.assertNotIn(lapsed_workspace, table.data)
        self.assertNotIn(withdrawn_workspace, table.data)
        self.assertNotIn(replaced_workspace, table.data)


class CDSAWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's CDSAWorkspace model."""

    def setUp(self):
        """Set up test class."""
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = factories.CDSAWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_shows_disease_term_if_required_by_duo_permission(self):
        """Displays the disease term if required by the DUO permission."""
        permission = DataUsePermissionFactory.create(requires_disease_term=True)
        obj = factories.CDSAWorkspaceFactory.create(
            data_use_permission=permission,
            disease_term="MONDO:0000045",
        )
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertContains(response, "(Term: MONDO:0000045)")

    def test_does_not_show_disease_term_if_not_required_by_duo_permission(self):
        """Does not display a disease term or parentheses if a disease term is not required by the DUO permission."""
        permission = DataUsePermissionFactory.create()
        obj = factories.CDSAWorkspaceFactory.create(
            data_use_permission=permission,
        )
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertNotContains(response, "(Term:")

    def test_render_available_data(self):
        """Test coverage for available_data display."""
        available_datas = AvailableDataFactory.create_batch(2)
        obj = factories.CDSAWorkspaceFactory.create()
        obj.available_data.add(*available_datas)
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertContains(response, available_datas[0].name)
        self.assertContains(response, available_datas[1].name)

    def test_render_duo_modifiers(self):
        """Test coverage for available_data display."""
        permission = DataUsePermissionFactory.create()
        modifiers = DataUseModifierFactory.create_batch(2)
        obj = factories.CDSAWorkspaceFactory.create(
            data_use_permission=permission,
        )
        obj.data_use_modifiers.add(*modifiers)
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertContains(response, modifiers[0].abbreviation)
        self.assertContains(response, modifiers[1].abbreviation)


class CDSAWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's CDSAWorkspace model."""

    api_success_code = 201

    def setUp(self):
        """Set up test class."""
        # The superclass uses the responses package to mock API responses.
        super().setUp()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.requester = UserFactory.create()
        self.workspace_type = "cdsa"

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:new", args=args)

    def test_creates_upload_workspace_without_duos(self):
        """Posting valid data to the form creates a workspace data object when using a custom adapter."""
        study = factories.StudyFactory.create()
        duo_permission = DataUsePermissionFactory.create()
        # Create an extra that won't be specified.
        DataUseModifierFactory.create()
        billing_project = BillingProjectFactory.create(name="test-billing-project")
        url = self.api_client.rawls_entry_point + "/api/workspaces"
        json_data = {
            "namespace": "test-billing-project",
            "name": "test-workspace",
            "attributes": {},
        }
        self.anvil_response_mock.add(
            responses.POST,
            url,
            status=self.api_success_code,
            match=[responses.matchers.json_params_matcher(json_data)],
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.workspace_type),
            {
                "billing_project": billing_project.pk,
                "name": "test-workspace",
                # Workspace data form.
                "workspacedata-TOTAL_FORMS": 1,
                "workspacedata-INITIAL_FORMS": 0,
                "workspacedata-MIN_NUM_FORMS": 1,
                "workspacedata-MAX_NUM_FORMS": 1,
                "workspacedata-0-study": study.pk,
                "workspacedata-0-data_use_permission": duo_permission.pk,
                "workspacedata-0-data_use_limitations": "test limitations",
                "workspacedata-0-acknowledgments": "test acknowledgments",
                "workspacedata-0-requested_by": self.requester.pk,
                "workspacedata-0-gsr_restricted": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.CDSAWorkspace.objects.count(), 1)
        new_workspace_data = models.CDSAWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.study, study)
        self.assertEqual(new_workspace_data.data_use_permission, duo_permission)
        self.assertEqual(new_workspace_data.data_use_limitations, "test limitations")
        self.assertEqual(new_workspace_data.acknowledgments, "test acknowledgments")
        self.assertEqual(new_workspace_data.requested_by, self.requester)

    def test_creates_upload_workspace_with_duo_modifiers(self):
        """Posting valid data to the form creates a workspace data object when using a custom adapter."""
        study = factories.StudyFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        data_use_modifier_1 = DataUseModifierFactory.create()
        data_use_modifier_2 = DataUseModifierFactory.create()
        # Create an extra that won't be specified.
        DataUseModifierFactory.create()
        billing_project = BillingProjectFactory.create(name="test-billing-project")
        url = self.api_client.rawls_entry_point + "/api/workspaces"
        json_data = {
            "namespace": "test-billing-project",
            "name": "test-workspace",
            "attributes": {},
        }
        self.anvil_response_mock.add(
            responses.POST,
            url,
            status=self.api_success_code,
            match=[responses.matchers.json_params_matcher(json_data)],
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.workspace_type),
            {
                "billing_project": billing_project.pk,
                "name": "test-workspace",
                # Workspace data form.
                "workspacedata-TOTAL_FORMS": 1,
                "workspacedata-INITIAL_FORMS": 0,
                "workspacedata-MIN_NUM_FORMS": 1,
                "workspacedata-MAX_NUM_FORMS": 1,
                "workspacedata-0-study": study.pk,
                "workspacedata-0-data_use_limitations": "test limitations",
                "workspacedata-0-acknowledgments": "test acknowledgments",
                "workspacedata-0-data_use_permission": data_use_permission.pk,
                "workspacedata-0-data_use_modifiers": [
                    data_use_modifier_1.pk,
                    data_use_modifier_2.pk,
                ],
                "workspacedata-0-requested_by": self.requester.pk,
                "workspacedata-0-gsr_restricted": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_workspace_data = models.CDSAWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.data_use_modifiers.count(), 2)
        self.assertIn(data_use_modifier_1, new_workspace_data.data_use_modifiers.all())
        self.assertIn(data_use_modifier_2, new_workspace_data.data_use_modifiers.all())

    def test_creates_upload_workspace_with_disease_term(self):
        """Posting valid data to the form creates a workspace data object when using a custom adapter."""
        study = factories.StudyFactory.create()
        data_use_permission = DataUsePermissionFactory.create(
            requires_disease_term=True
        )
        # Create an extra that won't be specified.
        billing_project = BillingProjectFactory.create(name="test-billing-project")
        url = self.api_client.rawls_entry_point + "/api/workspaces"
        json_data = {
            "namespace": "test-billing-project",
            "name": "test-workspace",
            "attributes": {},
        }
        self.anvil_response_mock.add(
            responses.POST,
            url,
            status=self.api_success_code,
            match=[responses.matchers.json_params_matcher(json_data)],
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.workspace_type),
            {
                "billing_project": billing_project.pk,
                "name": "test-workspace",
                # Workspace data form.
                "workspacedata-TOTAL_FORMS": 1,
                "workspacedata-INITIAL_FORMS": 0,
                "workspacedata-MIN_NUM_FORMS": 1,
                "workspacedata-MAX_NUM_FORMS": 1,
                "workspacedata-0-study": study.pk,
                "workspacedata-0-data_use_limitations": "test limitations",
                "workspacedata-0-acknowledgments": "test acknowledgments",
                "workspacedata-0-data_use_permission": data_use_permission.pk,
                "workspacedata-0-disease_term": "foo",
                "workspacedata-0-requested_by": self.requester.pk,
                "workspacedata-0-gsr_restricted": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_workspace_data = models.CDSAWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.disease_term, "foo")
