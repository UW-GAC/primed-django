from django.test import TestCase

from .. import helpers


class TestHelperMethods(TestCase):
    """Tests for methods in the helpers.py file."""

    def test_get_dbgap_dar_json_url_one_project(self):
        """get_dbgap_dar_json_url returns a string when one project id is specified."""
        self.assertIsInstance(helpers.get_dbgap_dar_json_url([1]), str)

    def test_get_dbgap_dar_json_url_two_projects(self):
        """get_dbgap_dar_json_url returns a string when two project ids are specified."""
        self.assertIsInstance(helpers.get_dbgap_dar_json_url([2]), str)

    def test_get_dbgap_dar_json_url_one_project_not_list(self):
        """get_dbgap_dar_json_url returns a string when one project id is specified but not in a list."""
        self.assertIsInstance(helpers.get_dbgap_dar_json_url(1), str)
