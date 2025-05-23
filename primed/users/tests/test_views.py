import json

import pytest
from allauth.socialaccount.models import SocialApp
from anvil_consortium_manager.models import AnVILProjectManagerAccess
from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    UserEmailEntryFactory,
)
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sites.models import Site
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.urls import reverse

from primed.cdsa.models import SignedAgreement
from primed.cdsa.tests.factories import (
    DataAffiliateAgreementFactory,
    MemberAgreementFactory,
    NonDataAffiliateAgreementFactory,
)
from primed.dbgap.tests.factories import dbGaPApplicationFactory
from primed.drupal_oauth_provider.provider import CustomProvider
from primed.primed_anvil.tests.factories import StudySiteFactory
from primed.users.forms import UserChangeForm
from primed.users.models import User
from primed.users.tests.factories import UserFactory
from primed.users.views import (
    UserAutocompleteView,
    UserLookupForm,
    UserRedirectView,
    UserUpdateView,
    user_detail_view,
)

pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    """
    TODO:
        extracting view initialization code as class-scoped fixture
        would be great if only pytest-django supported non-function-scoped
        fixture db access -- this is a work-in-progress for now:
        https://github.com/pytest-dev/pytest-django/pull/258
    """

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_success_url() == f"/users/{user.username}/"

    def test_get_object(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_object() == user

    def test_authenticated(self, client, user: User, rf: RequestFactory):
        client.force_login(user)
        user_update_url = reverse("users:update")
        response = client.get(user_update_url)

        assert response.status_code == 200

    def test_not_authenticated(self, client):
        user_update_url = reverse("users:update")
        response = client.get(user_update_url)

        assert response.status_code == 302

    def test_form_valid(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        request.user = user

        view.request = request

        # Initialize the form
        form = UserChangeForm()
        form.cleaned_data = dict()
        view.form_valid(form)

        messages_sent = [m.message for m in messages.get_messages(request)]
        assert messages_sent == ["Information successfully updated"]


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user

        view.request = request

        assert view.get_redirect_url() == f"/users/{user.username}/"


class TestUserDetailView:
    def test_authenticated(self, client, user: User, rf: RequestFactory):
        client.force_login(user)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_authenticated_with_verified_account(self, client, user: User, rf: RequestFactory):
        client.force_login(user)
        user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        AccountFactory.create(email="foo@bar.com", user=user, verified=True)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_authenticated_with_user_email_entry(self, client, user: User, rf: RequestFactory):
        client.force_login(user)
        user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        UserEmailEntryFactory.create(email="foo@bar.com", user=user)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_authenticated_with_unverified_account(self, client, user: User, rf: RequestFactory):
        client.force_login(user)
        AccountFactory.create(email="foo@bar.com", user=user, verified=False)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_authenticated_with_study_sites(self, client, user: User, rf: RequestFactory):
        client.force_login(user)
        study_site = StudySiteFactory.create()
        user.study_sites.add(study_site)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_not_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()

        response = user_detail_view(request, username=user.username)
        login_url = reverse(settings.LOGIN_URL)

        assert response.status_code == 302
        assert response["Location"] == f"{login_url}?next=/fake-url/"

    def test_staff_view_links(self, client, user: User, rf: RequestFactory):
        """Link to ACM account page is in response for users with STAFF_VIEW permission."""
        user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        client.force_login(user)
        account = AccountFactory.create(email="foo@bar.com", user=user, verified=True)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)
        assert account.get_absolute_url() in str(response.content)

    def test_view_links(self, client, user: User, rf: RequestFactory):
        """Link to ACM account page is not in response for users with VIEW permission."""
        user.user_permissions.add(Permission.objects.get(codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME))
        client.force_login(user)
        account = AccountFactory.create(email="foo@bar.com", user=user, verified=True)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)
        assert account.get_absolute_url() not in str(response.content)


class LoginViewTest(TestCase):
    def setUp(self):
        current_site = Site.objects.get_current()
        self.social_app = SocialApp.objects.create(
            provider=CustomProvider.id,
            name="DOA",
            client_id="test-client-id",
            secret="test-client-secret",
        )
        self.social_app.sites.add(current_site)

    def test_basic_login_view_render(self):
        response = self.client.get(reverse("account_login"))
        assert response.status_code == 200


class UserDetailTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserFactory.create()

    def test_data_access_my_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My data access mechanisms")
        self.assertContains(response, "dbGaP")
        self.assertContains(response, "Consortium data sharing agreements")

    def test_data_access_other_profile(self):
        other_user = UserFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(other_user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "My data access mechanisms")

    def test_dbgap_no_dbgap_applications(self):
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No dbGaP applications")
        self.assertIn("dbgap_applications", response.context)
        self.assertEqual(len(response.context["dbgap_applications"]), 0)

    def test_dbgap_pi_of_one_dbgap_application(self):
        dbgap_application = dbGaPApplicationFactory.create(principal_investigator=self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No dbGaP applications")
        self.assertContains(response, "Principal Investigator", count=1)
        self.assertContains(response, dbgap_application.dbgap_project_id)
        self.assertContains(response, dbgap_application.get_absolute_url())
        self.assertIn("dbgap_applications", response.context)
        self.assertEqual(len(response.context["dbgap_applications"]), 1)
        self.assertIn(dbgap_application, response.context["dbgap_applications"])

    def test_dbgap_pi_of_two_dbgap_applications(self):
        dbgap_application_1 = dbGaPApplicationFactory.create(principal_investigator=self.user)
        dbgap_application_2 = dbGaPApplicationFactory.create(principal_investigator=self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Principal Investigator", count=2)
        self.assertNotContains(response, "No dbGaP applications")
        self.assertContains(response, dbgap_application_1.dbgap_project_id)
        self.assertContains(response, dbgap_application_1.get_absolute_url())
        self.assertContains(response, dbgap_application_2.dbgap_project_id)
        self.assertContains(response, dbgap_application_2.get_absolute_url())
        self.assertIn("dbgap_applications", response.context)
        self.assertEqual(len(response.context["dbgap_applications"]), 2)
        self.assertIn(dbgap_application_1, response.context["dbgap_applications"])
        self.assertIn(dbgap_application_2, response.context["dbgap_applications"])

    def test_dbgap_collaborator_on_one_dbgap_application(self):
        dbgap_application = dbGaPApplicationFactory.create()
        dbgap_application.collaborators.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Collaborator", count=1)
        self.assertNotContains(response, "No dbGaP applications")
        self.assertContains(response, dbgap_application.dbgap_project_id)
        self.assertContains(response, dbgap_application.get_absolute_url())
        self.assertIn("dbgap_applications", response.context)
        self.assertEqual(len(response.context["dbgap_applications"]), 1)
        self.assertIn(dbgap_application, response.context["dbgap_applications"])

    def test_dbgap_collaborator_on_two_dbgap_applications(self):
        dbgap_application_1 = dbGaPApplicationFactory.create()
        dbgap_application_1.collaborators.add(self.user)
        dbgap_application_2 = dbGaPApplicationFactory.create()
        dbgap_application_2.collaborators.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Collaborator", count=2)
        self.assertNotContains(response, "No dbGaP applications")
        self.assertContains(response, dbgap_application_1.dbgap_project_id)
        self.assertContains(response, dbgap_application_1.get_absolute_url())
        self.assertContains(response, dbgap_application_2.dbgap_project_id)
        self.assertContains(response, dbgap_application_2.get_absolute_url())
        self.assertIn("dbgap_applications", response.context)
        self.assertEqual(len(response.context["dbgap_applications"]), 2)
        self.assertIn(dbgap_application_1, response.context["dbgap_applications"])
        self.assertIn(dbgap_application_2, response.context["dbgap_applications"])

    def test_dbgap_pi_and_collaborator(self):
        dbgap_application_1 = dbGaPApplicationFactory.create(principal_investigator=self.user)
        dbgap_application_2 = dbGaPApplicationFactory.create()
        dbgap_application_2.collaborators.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Principal Investigator")
        self.assertContains(response, "Collaborator")
        self.assertNotContains(response, "No dbGaP applications")
        self.assertContains(response, dbgap_application_1.dbgap_project_id)
        self.assertContains(response, dbgap_application_1.get_absolute_url())
        self.assertContains(response, dbgap_application_2.dbgap_project_id)
        self.assertContains(response, dbgap_application_2.get_absolute_url())
        self.assertIn("dbgap_applications", response.context)
        self.assertEqual(len(response.context["dbgap_applications"]), 2)
        self.assertIn(dbgap_application_1, response.context["dbgap_applications"])
        self.assertIn(dbgap_application_2, response.context["dbgap_applications"])

    def test_dbgap_pi_two_different_collaborators(self):
        dbgap_application = dbGaPApplicationFactory.create(principal_investigator=self.user)
        dbgap_application.collaborators.add(*UserFactory.create_batch(2))
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No dbGaP applications")
        self.assertContains(response, "Principal Investigator", count=1)
        self.assertContains(response, dbgap_application.dbgap_project_id)
        self.assertContains(response, dbgap_application.get_absolute_url())
        self.assertIn("dbgap_applications", response.context)
        self.assertEqual(len(response.context["dbgap_applications"]), 1)
        self.assertIn(dbgap_application, response.context["dbgap_applications"])

    def test_other_dbgap_applications(self):
        # Create an application for a different user.
        dbGaPApplicationFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No dbGaP applications")
        self.assertIn("dbgap_applications", response.context)
        self.assertEqual(len(response.context["dbgap_applications"]), 0)

    def test_cdsa_no_signed_agreements(self):
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No CDSAs")

    def test_cdsa_representative(self):
        agreement = MemberAgreementFactory.create(signed_agreement__representative=self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Representative", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_accessor_on_one_member_agreement(self):
        agreement = MemberAgreementFactory.create()
        agreement.signed_agreement.accessors.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accessor", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_accessor_on_one_data_affiliate_agreement(self):
        agreement = DataAffiliateAgreementFactory.create()
        agreement.signed_agreement.accessors.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accessor", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_accessor_on_one_non_data_affiliate_agreement(self):
        agreement = NonDataAffiliateAgreementFactory.create()
        agreement.signed_agreement.accessors.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accessor")
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_multiple_accessors(self):
        agreement = MemberAgreementFactory.create()
        agreement.signed_agreement.accessors.add(self.user, UserFactory.create())
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accessor", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_accessor_on_two_signed_agreements(self):
        agreement_1 = MemberAgreementFactory.create()
        agreement_2 = MemberAgreementFactory.create()
        agreement_1.signed_agreement.accessors.add(self.user)
        agreement_2.signed_agreement.accessors.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accessor", count=2)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement_1.signed_agreement.cc_id)
        self.assertContains(response, agreement_1.get_absolute_url())
        self.assertContains(response, agreement_2.signed_agreement.cc_id)
        self.assertContains(response, agreement_2.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 2)
        self.assertIn(agreement_1.signed_agreement, response.context["signed_agreements"])
        self.assertIn(agreement_2.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_two_accessors(self):
        other_user = UserFactory.create()
        agreement = DataAffiliateAgreementFactory.create()
        agreement.signed_agreement.accessors.add(self.user, other_user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accessor", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_uploader_on_one_signed_agreement(self):
        agreement = DataAffiliateAgreementFactory.create()
        agreement.uploaders.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Uploader", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_uploader_on_two_signed_agreements(self):
        agreement_1 = DataAffiliateAgreementFactory.create()
        agreement_1.uploaders.add(self.user)
        agreement_2 = DataAffiliateAgreementFactory.create()
        agreement_2.uploaders.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Uploader", count=2)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement_1.signed_agreement.cc_id)
        self.assertContains(response, agreement_1.get_absolute_url())
        self.assertContains(response, agreement_2.signed_agreement.cc_id)
        self.assertContains(response, agreement_2.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 2)
        self.assertIn(agreement_1.signed_agreement, response.context["signed_agreements"])
        self.assertIn(agreement_2.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_uploader_and_accessor(self):
        agreement = DataAffiliateAgreementFactory.create()
        agreement.signed_agreement.accessors.add(self.user)
        agreement.uploaders.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Uploader", count=1)
        self.assertContains(response, "Accessor", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_two_uploaders(self):
        other_user = UserFactory.create()
        agreement = DataAffiliateAgreementFactory.create()
        agreement.uploaders.add(self.user, other_user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Uploader", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_accessor_two_different_uploaders(self):
        agreement = DataAffiliateAgreementFactory.create()
        agreement.signed_agreement.accessors.add(self.user)
        uploaders = UserFactory.create_batch(2)
        agreement.uploaders.add(*uploaders)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Uploader")
        self.assertContains(response, "Accessor", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_uploader_two_different_accessors(self):
        agreement = DataAffiliateAgreementFactory.create()
        accessors = UserFactory.create_batch(2)
        agreement.signed_agreement.accessors.add(*accessors)
        agreement.uploaders.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Uploader", count=1)
        self.assertNotContains(response, "Accessor")
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement.signed_agreement.cc_id)
        self.assertContains(response, agreement.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 1)
        self.assertIn(agreement.signed_agreement, response.context["signed_agreements"])

    def test_cdsa_accessor_active_agreement_shown_correct_badge(self):
        agreement = MemberAgreementFactory.create(signed_agreement__status=SignedAgreement.StatusChoices.ACTIVE)
        agreement.signed_agreement.accessors.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="badge mx-2 bg-success">Active</span>', html=True)

    def test_cdsa_accessor_withdrawn_agreement_shown_correct_badge(self):
        agreement = MemberAgreementFactory.create(signed_agreement__status=SignedAgreement.StatusChoices.WITHDRAWN)
        agreement.signed_agreement.accessors.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="badge mx-2 bg-danger">Withdrawn</span>', html=True)

    def test_cdsa_accessor_replaced_agreement_shown_correct_badge(self):
        agreement = MemberAgreementFactory.create(signed_agreement__status=SignedAgreement.StatusChoices.REPLACED)
        agreement.signed_agreement.accessors.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="badge mx-2 bg-danger">Replaced</span>', html=True)

    def test_cdsa_accessor_lapsed_agreement_shown_correct_badge(self):
        agreement = MemberAgreementFactory.create(signed_agreement__status=SignedAgreement.StatusChoices.LAPSED)
        agreement.signed_agreement.accessors.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="badge mx-2 bg-danger">Lapsed</span>', html=True)

    def test_acm_staff_view(self):
        """Users with staff view permission see dbGaP application info."""
        staff_view_user = UserFactory.create()
        staff_view_user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        dbgap_application_1 = dbGaPApplicationFactory.create(principal_investigator=self.user)
        dbgap_application_2 = dbGaPApplicationFactory.create()
        dbgap_application_2.collaborators.add(self.user)
        # Add CDSA agreements.
        agreement_1 = MemberAgreementFactory.create()
        agreement_1.signed_agreement.accessors.add(self.user)
        agreement_2 = DataAffiliateAgreementFactory.create()
        agreement_2.uploaders.add(self.user)
        # Log in the user with staff view permission.
        self.client.force_login(staff_view_user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User data access mechanisms")
        # dbGap checks.
        self.assertContains(response, "Principal Investigator")
        self.assertContains(response, "Collaborator")
        self.assertNotContains(response, "No dbGaP applications")
        self.assertContains(response, dbgap_application_1.dbgap_project_id)
        self.assertContains(response, dbgap_application_1.get_absolute_url())
        self.assertContains(response, dbgap_application_2.dbgap_project_id)
        self.assertContains(response, dbgap_application_2.get_absolute_url())
        self.assertIn("dbgap_applications", response.context)
        self.assertEqual(len(response.context["dbgap_applications"]), 2)
        self.assertIn(dbgap_application_1, response.context["dbgap_applications"])
        self.assertIn(dbgap_application_2, response.context["dbgap_applications"])
        # CDSA checks.
        self.assertContains(response, "Accessor", count=1)
        self.assertContains(response, "Uploader", count=1)
        self.assertNotContains(response, "No CDSAs")
        self.assertContains(response, agreement_1.signed_agreement.cc_id)
        self.assertContains(response, agreement_1.get_absolute_url())
        self.assertContains(response, agreement_2.signed_agreement.cc_id)
        self.assertContains(response, agreement_2.get_absolute_url())
        self.assertIn("signed_agreements", response.context)
        self.assertEqual(len(response.context["signed_agreements"]), 2)
        self.assertIn(agreement_1.signed_agreement, response.context["signed_agreements"])
        self.assertIn(agreement_2.signed_agreement, response.context["signed_agreements"])

    def test_inactive_user_inactive_message(self):
        """Inactive user alert is shown for an inactive user."""
        user = UserFactory.create(is_active=False)
        self.client.force_login(self.user)
        response = self.client.get(user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This user is inactive.")

    def test_active_user_no_inactive_message(self):
        """Inactive user alert is not shown for an active user."""
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "This user is inactive.")

    def test_inactive_anvil_account_alert_is_inactive(self):
        """Alert is shown when AnVIL account is inactive."""
        account = AccountFactory.create(email="foo@bar.com", user=self.user, verified=True)
        account.status = account.INACTIVE_STATUS
        account.save()
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This account is inactive.")

    def test_inactive_anvil_account_alert_is_active(self):
        """Alert is not shown when AnVIL account is active."""
        AccountFactory.create(email="foo@bar.com", user=self.user, verified=True)
        self.client.force_login(self.user)
        response = self.client.get(self.user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "This account is inactive.")


class UserAutocompleteTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with the correct permissions.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("users:autocomplete", args=args)

    def get_view(self):
        """Return the view being tested."""
        return UserAutocompleteView.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url())

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_returns_all_instances(self):
        """Queryset returns all instances when there is no query."""
        UserFactory.create_batch(9)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        # The test user plus the ones we created in this test.
        self.assertEqual(len(returned_ids), 10)
        self.assertEqual(
            sorted(returned_ids),
            sorted([instance.pk for instance in User.objects.all()]),
        )

    def test_returns_correct_instance_match_name(self):
        """Queryset returns the correct instances when query matches the short_name."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "First Last"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_starting_with_query_name(self):
        """Queryset returns the correct instances when query matches the beginning of the short_name."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "Firs"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_containing_query_short_name(self):
        """Queryset returns the correct instances when the short_name contains the query."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "ast"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_case_insensitive_name(self):
        """Queryset returns the correct instances when query matches the beginning of the short_name."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "first last"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_match_email(self):
        """Queryset returns the correct instances when query matches the email."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "foo@bar.com"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_starting_with_query_email(self):
        """Queryset returns the correct instances when query matches the beginning of the email."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "foo"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_containing_query_email(self):
        """Queryset returns the correct instances when the email contains the query."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "bar"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_case_insensitive_email(self):
        """Queryset returns the correct instances when query matches the beginning of the email."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "FOO@BAR.COM"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_get_result_label(self):
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url())
        request.user = self.user
        view = UserAutocompleteView()
        view.setup(request)
        self.assertEqual(view.get_result_label(instance), "First Last (foo@bar.com)")

    def test_get_selected_result_label(self):
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url())
        request.user = self.user
        view = UserAutocompleteView()
        view.setup(request)
        self.assertEqual(view.get_selected_result_label(instance), "First Last (foo@bar.com)")

    def test_excludes_inactive_users(self):
        """Queryset excludes excludes inactive users."""
        UserFactory.create(is_active=False)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        # Only test user.
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids, [self.user.pk])


class UserLookup(TestCase):
    """Test for UserLookup view"""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = UserFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self):
        """Get the url for the view being tested."""
        return reverse("users:lookup")

    def test_form_class(self):
        """The form class is as expected."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("form", response.context_data)
        self.assertIsInstance(response.context_data["form"], UserLookupForm)

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        response = self.client.get(self.get_url())
        self.assertRedirects(response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url())

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_redirect_to_the_correct_profile_page(self):
        """The search view correctly redirect to the user profile page"""
        object = UserFactory.create(
            username="user1",
            password="passwd",
            email="user1@example.com",
        )
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"user": object.pk})
        self.assertRedirects(
            response,
            resolve_url(reverse("users:detail", kwargs={"username": object.username})),
        )

    def test_invalid_input(self):
        """Posting invalid data re-renders the form with an error."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {"user": -1},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors.keys()), 1)
        self.assertIn("user", form.errors.keys())
        self.assertEqual(len(form.errors["user"]), 1)
        self.assertIn("valid choice", form.errors["user"][0])

    def test_blank_user(self):
        """Posting invalid data does not create an object."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors.keys()), 1)
        self.assertIn("user", form.errors.keys())
        self.assertEqual(len(form.errors["user"]), 1)
        self.assertIn("required", form.errors["user"][0])

    def test_invalid_inactive_user(self):
        """Form is invalid with an inactive user."""
        object = UserFactory.create(
            username="user1",
            password="passwd",
            email="user1@example.com",
            is_active=False,
        )
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"user": object.pk})
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("user", form.errors)
        self.assertEqual(len(form.errors["user"]), 1)
        self.assertIn("valid choice", form.errors["user"][0])
