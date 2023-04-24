"""Tests for views related to the `cdsa` app."""

from anvil_consortium_manager.models import AnVILProjectManagerAccess
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .. import views
from . import factories

User = get_user_model()


class MemberAgreementDetailTest(TestCase):
    """Tests for the MemberAgreementDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        # Create an object test this with.
        self.obj = factories.MemberAgreementFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreements:members:detail", args=args)

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


class DataAffiliateAgreementDetailTest(TestCase):
    """Tests for the DataAffiliateAgreement view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        # Create an object test this with.
        self.obj = factories.DataAffiliateAgreementFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreements:data_affiliates:detail", args=args)

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


class NonDataAffiliateAgreementDetailTest(TestCase):
    """Tests for the NonDataAffiliateAgreement view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        # Create an object test this with.
        self.obj = factories.NonDataAffiliateAgreementFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreements:non_data_affiliates:detail", args=args)

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
