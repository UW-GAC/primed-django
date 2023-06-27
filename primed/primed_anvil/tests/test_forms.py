from django.test import TestCase

from primed.users.tests.factories import UserFactory

from .. import forms


class UserSearchFormTest(TestCase):

    form_class = forms.UserSearchForm

    def setUp(self):
        """Create a user for use in the form."""
        self.user = UserFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "user": self.user.name,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_name(self):
        """Form is invalid when missing name."""
        form_data = {}
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("user", form.errors)
        self.assertEqual(len(form.errors["user"]), 1)
        self.assertIn("required", form.errors["user"][0])
