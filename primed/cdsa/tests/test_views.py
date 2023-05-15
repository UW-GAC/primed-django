"""Tests for views related to the `cdsa` app."""

from datetime import date

import responses
from anvil_consortium_manager.models import (
    AnVILProjectManagerAccess,
    ManagedGroup,
    Workspace,
)
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
        self.assertEqual(ManagedGroup.objects.count(), 1)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "TEST_PRIMED_CDSA_ACCESS_2345")
        self.assertTrue(new_group.is_managed_by_app)

    @override_settings(ANVIL_DATA_ACCESS_GROUP_PREFIX="foo")
    def test_creates_anvil_groups_different_setting(self):
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
        self.assertEqual(ManagedGroup.objects.count(), 1)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "foo_CDSA_ACCESS_2345")
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
        self.assertEqual(ManagedGroup.objects.count(), 2)
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
        return reverse("cdsa:agreements:non_data_affiliates:new", args=args)

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
        self.assertEqual(ManagedGroup.objects.count(), 1)
        self.assertIsInstance(new_agreement.anvil_access_group, ManagedGroup)
        self.assertEqual(
            new_agreement.anvil_access_group.name, "TEST_PRIMED_CDSA_ACCESS_1234"
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
        print(form.errors)
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
        self.assertEqual(ManagedGroup.objects.count(), 1)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "TEST_PRIMED_CDSA_ACCESS_2345")
        self.assertTrue(new_group.is_managed_by_app)

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
        self.assertEqual(ManagedGroup.objects.count(), 1)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "foo_CDSA_ACCESS_2345")
        self.assertTrue(new_group.is_managed_by_app)

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
        self.assertEqual(ManagedGroup.objects.count(), 0)

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


class SignedAgreementAuditTest(TestCase):
    """Tests for the SignedAgreementAudit view."""

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
        self.anvil_cdsa_group = ManagedGroupFactory.create(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "cdsa:audit:agreements",
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
            signed_agreement_audit.SignedAgreementAccessAudit.VALID_PRIMARY_CDSA,
        )
        self.assertIsNone(table.rows[0].get_cell_value("action"))

    def test_context_verified_table_no_access(self):
        """verified_table shows a record when audit has verified no access."""
        member_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False
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
            signed_agreement_audit.SignedAgreementAccessAudit.NO_PRIMARY_CDSA,
        )
        self.assertIsNone(table.rows[0].get_cell_value("action"))

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
            signed_agreement_audit.SignedAgreementAccessAudit.VALID_PRIMARY_CDSA,
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
            signed_agreement_audit.SignedAgreementAccessAudit.NO_PRIMARY_CDSA,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))


class CDSAWorkspaceAuditTest(TestCase):
    """Tests for the SignedAgreementAudit view."""

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
        self.anvil_cdsa_group = ManagedGroupFactory.create(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "cdsa:audit:workspaces",
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
            workspace_audit.WorkspaceAccessAudit.VALID_PRIMARY_CDSA,
        )
        self.assertIsNone(table.rows[0].get_cell_value("action"))

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
            workspace_audit.WorkspaceAccessAudit.NO_PRIMARY_CDSA,
        )
        self.assertIsNone(table.rows[0].get_cell_value("action"))

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
            workspace_audit.WorkspaceAccessAudit.VALID_PRIMARY_CDSA,
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
            workspace_audit.WorkspaceAccessAudit.NO_PRIMARY_CDSA,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))


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

    def test_table_three_rows(self):
        """Three rows are shown if there are three CDSAWorkspaces objects."""
        factories.CDSAWorkspaceFactory.create_batch(3)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 3)


class CDSAWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's CDSAWorkspace model."""

    def setUp(self):
        """Set up test class."""
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
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
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
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
            },
        )
        self.assertEqual(response.status_code, 302)
        new_workspace_data = models.CDSAWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.disease_term, "foo")
