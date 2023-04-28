"""Tests for views related to the `cdsa` app."""

from datetime import date

import responses
from anvil_consortium_manager.models import AnVILProjectManagerAccess, ManagedGroup
from anvil_consortium_manager.tests.factories import ManagedGroupFactory
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
from primed.users.tests.factories import UserFactory

from .. import forms, models, tables, views
from . import factories

User = get_user_model()


class SignedAgreementListTest(TestCase):
    """Tests for the SignedAgreementList view."""

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

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreements:list", args=args)

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
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreements:members:new", args=args)

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
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
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
            response.context_data["formset"], forms.MemberAgreementInlineFormset
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                # "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": 999,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(ManagedGroup.objects.count(), 1)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "TEST_PRIMED_CDSA_ACCESS_2345")
        self.assertTrue(new_group.is_managed_by_app)

    @override_settings(ANVIL_CDSA_GROUP_PREFIX="foo")
    def test_creates_anvil_access_group_different_setting(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study_site = StudySiteFactory.create()
        api_url = self.api_client.sam_entry_point + "/api/groups/v1/foo_2345"
        self.anvil_response_mock.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(ManagedGroup.objects.count(), 1)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "foo_2345")
        self.assertTrue(new_group.is_managed_by_app)

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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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
        self.assertEqual(ManagedGroup.objects.count(), 0)

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
                "memberagreement-TOTAL_FORMS": 1,
                "memberagreement-INITIAL_FORMS": 0,
                "memberagreement-MIN_NUM_FORMS": 1,
                "memberagreement-MAX_NUM_FORMS": 1,
                "memberagreement-0-study_site": study_site.pk,
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


class MemberAgreementListTest(TestCase):
    """Tests for the MemberAgreementList view."""

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

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreements:members:list", args=args)

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
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreements:data_affiliates:new", args=args)

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
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
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
            response.context_data["formset"], forms.DataAffiliateAgreementInlineFormset
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
        self.assertEqual(ManagedGroup.objects.count(), 2)
        self.assertIsInstance(new_agreement.anvil_access_group, ManagedGroup)
        self.assertEqual(
            new_agreement.anvil_access_group.name, "TEST_PRIMED_CDSA_ACCESS_1234"
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                # "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": 999,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        # An upload group and an access group
        self.assertEqual(ManagedGroup.objects.count(), 2)
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

    @override_settings(ANVIL_CDSA_GROUP_PREFIX="foo_ACCESS")
    def test_creates_anvil_access_group_different_setting(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        representative = UserFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        study = StudyFactory.create()
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/foo_ACCESS_2345",
            status=201,
            json={"message": "mock message"},
        )
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/foo_UPLOAD_2345",
            status=201,
            json={"message": "mock message"},
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.SignedAgreement.objects.latest("pk")
        self.assertEqual(ManagedGroup.objects.count(), 2)
        # A new group was created.
        self.assertEqual(new_object.anvil_access_group.name, "foo_ACCESS_2345")
        self.assertTrue(new_object.anvil_access_group.is_managed_by_app)
        # An upload group was created.
        self.assertEqual(
            new_object.dataaffiliateagreement.anvil_upload_group.name, "foo_UPLOAD_2345"
        )
        self.assertTrue(
            new_object.dataaffiliateagreement.anvil_upload_group.is_managed_by_app
        )

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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
        self.assertEqual(ManagedGroup.objects.count(), 0)

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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
        self.assertEqual(ManagedGroup.objects.count(), 0)

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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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
                "dataaffiliateagreement-TOTAL_FORMS": 1,
                "dataaffiliateagreement-INITIAL_FORMS": 0,
                "dataaffiliateagreement-MIN_NUM_FORMS": 1,
                "dataaffiliateagreement-MAX_NUM_FORMS": 1,
                "dataaffiliateagreement-0-study": study.pk,
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


class DataAffiliateAgreementListTest(TestCase):
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

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreements:data_affiliates:list", args=args)

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


class NonDataAffiliateAgreementListTest(TestCase):
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

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("cdsa:agreements:non_data_affiliates:list", args=args)

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
