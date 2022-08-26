import json

import responses
from anvil_consortium_manager import models as acm_models
from anvil_consortium_manager import views as acm_views
from anvil_consortium_manager.tests import factories as acm_factories
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http.response import Http404
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .. import models, tables, views
from . import factories

# from .utils import AnVILAPIMockTestMixin

User = get_user_model()


class StudyDetailTest(TestCase):
    """Tests for the StudyDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:studies:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.StudyDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = self.model_factory.create()
        request = self.factory.get(self.get_url(obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=obj.pk)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_view_status_code_with_invalid_pk(self):
        """Raises a 404 error with an invalid object pk."""
        obj = self.model_factory.create()
        request = self.factory.get(self.get_url(obj.pk + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, pk=obj.pk + 1)


class StudyAutocompleteTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with the correct permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:studies:autocomplete", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.StudyAutocomplete.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
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

    def test_returns_all_objects(self):
        """Queryset returns all objects when there is no query."""
        objects = factories.StudyFactory.create_batch(10)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 10)
        self.assertEqual(
            sorted(returned_ids), sorted([object.pk for object in objects])
        )

    def test_returns_correct_object_match_short_name(self):
        """Queryset returns the correct objects when query matches the short_name."""
        object = factories.StudyFactory.create(
            short_name="test", full_name="other study"
        )
        request = self.factory.get(self.get_url(), {"q": "test"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_starting_with_query_short_name(self):
        """Queryset returns the correct objects when query matches the beginning of the short_name."""
        object = factories.StudyFactory.create(
            short_name="test", full_name="other study"
        )
        request = self.factory.get(self.get_url(), {"q": "test"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_containing_query_short_name(self):
        """Queryset returns the correct objects when the short_name contains the query."""
        object = factories.StudyFactory.create(
            short_name="test", full_name="other study"
        )
        request = self.factory.get(self.get_url(), {"q": "es"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_case_insensitive_short_name(self):
        """Queryset returns the correct objects when query matches the beginning of the short_name."""
        object = factories.StudyFactory.create(
            short_name="TEST", full_name="other study"
        )
        request = self.factory.get(self.get_url(), {"q": "test"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_match_full_name(self):
        """Queryset returns the correct objects when query matches the full_name."""
        object = factories.StudyFactory.create(
            short_name="other", full_name="test study"
        )
        request = self.factory.get(self.get_url(), {"q": "test study"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_starting_with_query_full_name(self):
        """Queryset returns the correct objects when query matches the beginning of the full_name."""
        object = factories.StudyFactory.create(
            short_name="other", full_name="test study"
        )
        request = self.factory.get(self.get_url(), {"q": "test"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_containing_query_full_name(self):
        """Queryset returns the correct objects when the full_name contains the query."""
        object = factories.StudyFactory.create(
            short_name="other", full_name="test study"
        )
        request = self.factory.get(self.get_url(), {"q": "stu"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_case_insensitive_full_name(self):
        """Queryset returns the correct objects when query matches the beginning of the full_name."""
        object = factories.StudyFactory.create(
            short_name="other", full_name="TEST STUDY"
        )
        request = self.factory.get(self.get_url(), {"q": "test study"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)


class dbGaPWorkspaceListTest(TestCase):
    """Tests of the anvil_consortium_manager WorkspaceList view using this app's dbGaPWorkspaceAdapter."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.workspace_type = "dbgap"

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return acm_views.WorkspaceListByType.as_view()

    def test_view_has_correct_table_class(self):
        """The view has the correct table class in the context."""
        request = self.factory.get(self.get_url(self.workspace_type))
        request.user = self.user
        response = self.get_view()(request, workspace_type=self.workspace_type)
        self.assertIn("table", response.context_data)
        self.assertIsInstance(
            response.context_data["table"], tables.dbGaPWorkspaceTable
        )


class dbGaPWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's dbGaPWorkspace model."""

    api_success_code = 201

    def setUp(self):
        """Set up test class."""
        # The superclass uses the responses package to mock API responses.
        super().setUp()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
        )
        self.workspace_type = "dbgap"

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:new", args=args)

    def get_api_url(self, billing_project_name, workspace_name):
        """Return the Terra API url for a given billing project and workspace."""
        return (
            self.entry_point
            + "/api/workspaces/"
            + billing_project_name
            + "/"
            + workspace_name
        )

    def test_creates_upload_workspace(self):
        """Posting valid data to the form creates a workspace data object when using a custom adapter."""
        study = factories.StudyFactory.create()
        data_use_permission = factories.DataUsePermissionFactory.create()
        data_use_modifier_1 = factories.DataUseModifierFactory.create()
        data_use_modifier_2 = factories.DataUseModifierFactory.create()
        # Create an extra that won't be specified.
        factories.DataUseModifierFactory.create()
        billing_project = acm_factories.BillingProjectFactory.create(
            name="test-billing-project"
        )
        url = self.entry_point + "/api/workspaces"
        json_data = {
            "namespace": "test-billing-project",
            "name": "test-workspace",
            "attributes": {},
        }
        responses.add(
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
                "workspacedata-0-phs": 1,
                "workspacedata-0-version": 2,
                "workspacedata-0-participant_set": 3,
                "workspacedata-0-full_consent_code": "GRU-TEST",
                "workspacedata-0-data_use_limitations": "test limitations",
                "workspacedata-0-data_use_permission": data_use_permission.pk,
                "workspacedata-0-data_use_modifiers": [
                    data_use_modifier_1.pk,
                    data_use_modifier_2.pk,
                ],
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = acm_models.Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.dbGaPWorkspace.objects.count(), 1)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.study, study)
        self.assertEqual(new_workspace_data.phs, 1)
        self.assertEqual(new_workspace_data.version, 2)
        self.assertEqual(new_workspace_data.participant_set, 3)
        self.assertEqual(new_workspace_data.full_consent_code, "GRU-TEST")
        self.assertEqual(new_workspace_data.data_use_limitations, "test limitations")
        self.assertEqual(new_workspace_data.data_use_permission, data_use_permission)
        self.assertEqual(new_workspace_data.data_use_modifiers.count(), 2)
        self.assertIn(data_use_modifier_1, new_workspace_data.data_use_modifiers.all())
        self.assertIn(data_use_modifier_2, new_workspace_data.data_use_modifiers.all())
        responses.assert_call_count(url, 1)


class dbGaPWorkspaceImportTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceImport view from ACM with this app's dbGaPWorkspace model."""

    api_success_code = 200

    def setUp(self):
        """Set up test class."""
        # The superclass uses the responses package to mock API responses.
        super().setUp()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
        )
        self.workspace_type = "dbgap"

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:import", args=args)

    def get_api_url(self, billing_project_name, workspace_name):
        """Return the Terra API url for a given billing project and workspace."""
        return (
            self.entry_point
            + "/api/workspaces/"
            + billing_project_name
            + "/"
            + workspace_name
        )

    def get_api_json_response(
        self, billing_project, workspace, authorization_domains=[], access="OWNER"
    ):
        """Return a pared down version of the json response from the AnVIL API with only fields we need."""
        json_data = {
            "accessLevel": access,
            "owners": [],
            "workspace": {
                "authorizationDomain": [
                    {"membersGroupName": x} for x in authorization_domains
                ],
                "name": workspace,
                "namespace": billing_project,
            },
        }
        return json_data

    def test_creates_dbgap_workspace(self):
        """Posting valid data to the form creates an UploadWorkspace object."""
        study = factories.StudyFactory.create()
        data_use_permission = factories.DataUsePermissionFactory.create()
        data_use_modifier_1 = factories.DataUseModifierFactory.create()
        data_use_modifier_2 = factories.DataUseModifierFactory.create()
        # Create an extra that won't be specified.
        factories.DataUseModifierFactory.create()
        billing_project = acm_factories.BillingProjectFactory.create(
            name="billing-project"
        )
        workspace_name = "workspace"
        # Available workspaces API call.
        workspace_list_url = self.entry_point + "/api/workspaces"
        responses.add(
            responses.GET,
            workspace_list_url,
            match=[
                responses.matchers.query_param_matcher(
                    {"fields": "workspace.namespace,workspace.name,accessLevel"}
                )
            ],
            status=200,
            json=[self.get_api_json_response(billing_project.name, workspace_name)],
        )
        url = self.get_api_url(billing_project.name, workspace_name)
        responses.add(
            responses.GET,
            url,
            status=self.api_success_code,
            json=self.get_api_json_response(billing_project.name, workspace_name),
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.workspace_type),
            {
                "workspace": billing_project.name + "/" + workspace_name,
                # Workspace data form.
                "workspacedata-TOTAL_FORMS": 1,
                "workspacedata-INITIAL_FORMS": 0,
                "workspacedata-MIN_NUM_FORMS": 1,
                "workspacedata-MAX_NUM_FORMS": 1,
                "workspacedata-0-study": study.pk,
                "workspacedata-0-phs": 1,
                "workspacedata-0-version": 2,
                "workspacedata-0-participant_set": 3,
                "workspacedata-0-full_consent_code": "GRU-TEST",
                "workspacedata-0-data_use_limitations": "test limitations",
                "workspacedata-0-data_use_permission": data_use_permission.pk,
                "workspacedata-0-data_use_modifiers": [
                    data_use_modifier_1.pk,
                    data_use_modifier_2.pk,
                ],
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = acm_models.Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.dbGaPWorkspace.objects.count(), 1)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.study, study)
        self.assertEqual(new_workspace_data.phs, 1)
        self.assertEqual(new_workspace_data.version, 2)
        self.assertEqual(new_workspace_data.participant_set, 3)
        self.assertEqual(new_workspace_data.full_consent_code, "GRU-TEST")
        self.assertEqual(new_workspace_data.data_use_limitations, "test limitations")
        self.assertEqual(new_workspace_data.data_use_permission, data_use_permission)
        self.assertEqual(new_workspace_data.data_use_modifiers.count(), 2)
        self.assertIn(data_use_modifier_1, new_workspace_data.data_use_modifiers.all())
        self.assertIn(data_use_modifier_2, new_workspace_data.data_use_modifiers.all())
        responses.assert_call_count(url, 1)
