from anvil_consortium_manager.models import AnVILProjectManagerAccess
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.urls import reverse

from primed.users.tests.factories import UserFactory

from .. import views
from . import factories


class DataUsePermissionListTest(TestCase):
    """Tests for the DataUsePermissionList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with staff view permission.
        self.user = UserFactory.create(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("duo:data_use_permissions:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.DataUsePermissionList.as_view()

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
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = UserFactory.create(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_no_roots(self):
        """Template renders with no root nodes."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 0)

    def test_one_root(self):
        """Template renders with one root node."""
        root = factories.DataUsePermissionFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 1)
        self.assertIn(root, response.context_data["roots"])

    def test_one_root_one_child(self):
        """Template renders with one root node and one child node."""
        root = factories.DataUsePermissionFactory.create()
        child = factories.DataUsePermissionFactory.create(parent=root)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 1)
        self.assertIn(root, response.context_data["roots"])
        self.assertNotIn(child, response.context_data["roots"])

    def test_one_root_one_grandchild(self):
        """Template renders with one root node and one child node."""
        root = factories.DataUsePermissionFactory.create()
        child = factories.DataUsePermissionFactory.create(parent=root)
        grandchild = factories.DataUsePermissionFactory.create(parent=child)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 1)
        self.assertIn(root, response.context_data["roots"])
        self.assertNotIn(child, response.context_data["roots"])
        self.assertNotIn(grandchild, response.context_data["roots"])

    def test_two_roots(self):
        """Template renders with two root nodes."""
        root_1 = factories.DataUsePermissionFactory.create()
        root_2 = factories.DataUsePermissionFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 2)
        self.assertIn(root_1, response.context_data["roots"])
        self.assertIn(root_2, response.context_data["roots"])


class DataUsePermissionDetailTest(TestCase):
    """Tests for the DataUsePermissionDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with view permission.
        self.user = UserFactory.create(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("duo:data_use_permissions:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.DataUsePermissionDetail.as_view()

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
        object = factories.DataUsePermissionFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(object.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = UserFactory.create(username="test-none", password="test-none")
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, id=1)

    def test_object_does_not_exist(self):
        """Http404 is raised when object does not exist."""
        request = self.factory.get(self.get_url("foo"))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, id="foo")


class DataUseModifierListTest(TestCase):
    """Tests for the DataUseModifierList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = UserFactory.create(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("duo:data_use_modifiers:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.DataUseModifierList.as_view()

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
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = UserFactory.create(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_no_roots(self):
        """Template renders with no root nodes."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 0)

    def test_one_root(self):
        """Template renders with one root node."""
        root = factories.DataUseModifierFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 1)
        self.assertIn(root, response.context_data["roots"])

    def test_one_root_one_child(self):
        """Template renders with one root node and one child node."""
        root = factories.DataUseModifierFactory.create()
        child = factories.DataUseModifierFactory.create(parent=root)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 1)
        self.assertIn(root, response.context_data["roots"])
        self.assertNotIn(child, response.context_data["roots"])

    def test_one_root_one_grandchild(self):
        """Template renders with one root node and one child node."""
        root = factories.DataUseModifierFactory.create()
        child = factories.DataUseModifierFactory.create(parent=root)
        grandchild = factories.DataUseModifierFactory.create(parent=child)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 1)
        self.assertIn(root, response.context_data["roots"])
        self.assertNotIn(grandchild, response.context_data["roots"])

    def test_two_roots(self):
        """Template renders with two root nodes."""
        root_1 = factories.DataUseModifierFactory.create()
        root_2 = factories.DataUseModifierFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("roots", response.context_data)
        self.assertEqual(len(response.context_data["roots"]), 2)
        self.assertIn(root_1, response.context_data["roots"])
        self.assertIn(root_2, response.context_data["roots"])


class DataUseModifierDetailTest(TestCase):
    """Tests for the DataUseModifierDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = UserFactory.create(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("duo:data_use_modifiers:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.DataUseModifierDetail.as_view()

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
        object = factories.DataUseModifierFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(object.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = UserFactory.create(username="test-none", password="test-none")
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, id=1)

    def test_object_does_not_exist(self):
        """Http404 is raised when object does not exist."""
        request = self.factory.get(self.get_url("foo"))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, id="foo")
