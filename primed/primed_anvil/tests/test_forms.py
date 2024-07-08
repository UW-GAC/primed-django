"""Test forms for the `collaborative_analysis` app."""

from anvil_consortium_manager.models import ManagedGroup
from anvil_consortium_manager.tests.factories import BillingProjectFactory, ManagedGroupFactory, WorkspaceFactory
from django.core.exceptions import NON_FIELD_ERRORS
from django.test import TestCase
from faker import Faker

from .. import forms

fake = Faker()


class WorkspaceAuthDomainDisabledFormTest(TestCase):
    """Tests for the WorkspaceAuthDomainDisabledForm class."""

    form_class = forms.WorkspaceAuthDomainDisabledForm

    def test_valid(self):
        """Form is valid with necessary input."""
        billing_project = BillingProjectFactory.create()
        form_data = {
            "billing_project": billing_project,
            "name": "test-workspace",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_with_note(self):
        """Form is valid with necessary input and note is specified."""
        billing_project = BillingProjectFactory.create()
        form_data = {
            "billing_project": billing_project,
            "name": "test-workspace",
            "note": "test note",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_with_is_requester_pays(self):
        """Form is valid with necessary input and note is specified."""
        billing_project = BillingProjectFactory.create()
        form_data = {
            "billing_project": billing_project,
            "name": "test-workspace",
            "note": "test note",
            "is_requester_pays": True,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_billing_project(self):
        """Form is invalid when missing billing_project_name."""
        form_data = {"name": "test-workspace"}
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("billing_project", form.errors)
        self.assertEqual(len(form.errors), 1)

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing billing_project_name."""
        billing_project = BillingProjectFactory.create()
        form_data = {"billing_project": billing_project}
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertEqual(len(form.errors), 1)

    def test_one_authorization_domain_ignored(self):
        billing_project = BillingProjectFactory.create()
        ManagedGroupFactory.create()
        form_data = {
            "billing_project": billing_project,
            "name": "test-workspace",
            "authorization_domains": ManagedGroup.objects.all(),
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data["authorization_domains"]), 0)

    def test_two_authorization_domains_ignored(self):
        billing_project = BillingProjectFactory.create()
        ManagedGroupFactory.create_batch(2)
        form_data = {
            "billing_project": billing_project,
            "name": "test-workspace",
            "authorization_domains": ManagedGroup.objects.all(),
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data["authorization_domains"]), 0)

    def test_invalid_not_user_of_billing_project(self):
        billing_project = BillingProjectFactory.create(has_app_as_user=False)
        form_data = {
            "billing_project": billing_project,
            "name": "test-workspace",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("billing_project", form.errors)
        self.assertEqual(len(form.errors["billing_project"]), 1)
        self.assertIn("has_app_as_user", form.errors["billing_project"][0])

    def test_invalid_case_insensitive_duplicate(self):
        """Cannot validate with the same case-insensitive name in the same billing project as an existing workspace."""
        billing_project = BillingProjectFactory.create()
        name = "AbAbA"
        WorkspaceFactory.create(billing_project=billing_project, name=name)
        form_data = {"billing_project": billing_project, "name": name.lower()}
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn(NON_FIELD_ERRORS, form.errors)
        self.assertEqual(len(form.errors[NON_FIELD_ERRORS]), 1)
        self.assertIn("already exists", form.errors[NON_FIELD_ERRORS][0])

    def test_auth_domain_excluded(self):
        "Form can be instantiated when auth domain is excluded from the form."

        class TestForm(forms.WorkspaceAuthDomainDisabledForm):
            class Meta(forms.WorkspaceAuthDomainDisabledForm.Meta):
                exclude = ["authorization_domains"]

        form = TestForm()
        self.assertNotIn("authorization_domains", form.fields)
