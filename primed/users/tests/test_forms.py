"""
Module for all Form Tests.
"""

import pytest
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from primed.users.forms import UserCreationForm, UserLookupForm
from primed.users.models import User
from primed.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestUserCreationForm:
    """
    Test class for all tests related to the UserCreationForm
    """

    def test_username_validation_error_msg(self, user: User):
        """
        Tests UserCreation Form's unique validator functions correctly by testing:
            1) A new user with an existing username cannot be added.
            2) Only 1 error is raised by the UserCreation Form
            3) The desired error message is raised
        """

        # The user already exists,
        # hence cannot be created.
        form = UserCreationForm(
            {
                "username": user.username,
                "password1": user.password,
                "password2": user.password,
            }
        )

        assert not form.is_valid()
        assert len(form.errors) == 1
        assert "username" in form.errors
        assert form.errors["username"][0] == _("This username has already been taken.")


class UserLookupFormTest(TestCase):
    form_class = UserLookupForm

    def test_valid(self):
        """Form is valid with necessary input."""
        user_obj = UserFactory.create()
        form_data = {
            "user": user_obj,
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

    def test_inactive_user(self):
        """Form is invalid when user is inactive."""
        user_obj = UserFactory.create(is_active=False)
        form_data = {
            "user": user_obj,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("user", form.errors)
        self.assertEqual(len(form.errors["user"]), 1)
        self.assertIn("valid choice", form.errors["user"][0])
