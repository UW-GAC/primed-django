import json
import time

import responses
from django.conf import settings
from django.test import TestCase
from marshmallow_jsonapi import Schema, fields

from primed.users.audit import (
    audit_drupal_study_sites,
    get_drupal_json_api,
    get_study_sites,
)
from primed.users.models import StudySite


class StudySiteSchema(Schema):
    id = fields.Str(dump_only=True)
    title = fields.Str()
    field_long_name = fields.Str()
    drupal_internal__nid = fields.Str()
    # document_meta = fields.DocumentMeta()

    class Meta:
        type_ = "node--study_site_or_center"


class UserSchema(Schema):
    drupal_internal__uid = fields.Str()
    name = fields.Str()
    mail = fields.Str()
    field_given_first_name_s_ = fields.Str()
    field_examples_family_last_name_ = fields.Str()
    field_study_site_or_center = fields.Relationship(schema="StudySiteSchema")

    class Meta:
        type_ = "users"


# def debug_requests_on():
#     """Switches on logging of the requests module."""
#     HTTPConnection.debuglevel = 1

#     logging.basicConfig()
#     logging.getLogger().setLevel(logging.DEBUG)
#     requests_log = logging.getLogger("requests.packages.urllib3")
#     requests_log.setLevel(logging.DEBUG)
#     requests_log.propagate = True


TEST_STUDY_SITE_DATA = [
    {
        "id": "1",
        "drupal_internal__nid": "1",
        "title": "SS1",
        "field_long_name": "S S 1",
        # "document_meta": {"page": {"offset": 10}},
    },
    {
        "id": "2",
        "drupal_internal__nid": "2",
        "title": "SS2",
        "field_long_name": "S S 2",
        # "document_meta": {"page": {"offset": 10}},
    },
]


class TestStudySiteAudit(TestCase):
    """General tests of the user audit"""

    def setUp(self):
        # debug_requests_on()
        super().setUp()
        fake_time = time.time()
        self.token = {
            "token_type": "Bearer",
            "access_token": "asdfoiw37850234lkjsdfsdfTEST",
            "refresh_token": "sldvafkjw34509s8dfsdfTEST",
            "expires_in": 3600,
            "expires_at": fake_time + 3600,
        }

    def add_fake_study_sites_response(self):
        url_path = f"{settings.DRUPAL_SITE_URL}/jsonapi/node/study_site_or_center/"
        responses.get(
            url=url_path,
            body=json.dumps(StudySiteSchema(many=True).dump(TEST_STUDY_SITE_DATA)),
        )

    def get_fake_json_api(self):
        token_url = f"{settings.DRUPAL_SITE_URL}/oauth/token"
        responses.post(url=token_url, body=json.dumps(self.token))
        return get_drupal_json_api()

    @responses.activate
    def test_get_json_api(self):
        json_api = self.get_fake_json_api()
        # print(f"JSONAPI: {json_api.requests.config.AUTH._client.token}")
        assert (
            json_api.requests.config.AUTH._client.token["access_token"]
            == self.token["access_token"]
        )

    @responses.activate
    def test_get_study_sites(self):
        json_api = self.get_fake_json_api()
        self.add_fake_study_sites_response()
        study_sites = get_study_sites(json_api=json_api)

        for test_study_site in TEST_STUDY_SITE_DATA:

            assert (
                test_study_site["field_long_name"]
                == study_sites[test_study_site["drupal_internal__nid"]]["full_name"]
            )
            assert (
                test_study_site["title"]
                == study_sites[test_study_site["drupal_internal__nid"]]["short_name"]
            )
            assert (
                test_study_site["drupal_internal__nid"]
                == study_sites[test_study_site["drupal_internal__nid"]]["node_id"]
            )

    @responses.activate
    def test_audit_study_sites_no_update(self):
        json_api = self.get_fake_json_api()
        self.add_fake_study_sites_response()
        study_sites = get_study_sites(json_api=json_api)
        audit_results = audit_drupal_study_sites(
            study_sites=study_sites, should_update=False
        )
        assert audit_results.encountered_issues() is False
        assert StudySite.objects.all().count() == 0

    @responses.activate
    def test_audit_study_sites_with_new_sites(self):
        json_api = self.get_fake_json_api()
        self.add_fake_study_sites_response()
        study_sites = get_study_sites(json_api=json_api)
        audit_results = audit_drupal_study_sites(
            study_sites=study_sites, should_update=True
        )
        assert audit_results.encountered_issues() is False
        assert audit_results.count_new_rows() == 2
        assert StudySite.objects.all().count() == 2
        assert StudySite.objects.filter(
            short_name=TEST_STUDY_SITE_DATA[0]["title"]
        ).exists()

    @responses.activate
    def test_audit_study_sites_with_site_update(self):
        StudySite.objects.create(
            drupal_node_id=TEST_STUDY_SITE_DATA[0]["drupal_internal__nid"],
            short_name=TEST_STUDY_SITE_DATA[0]["title"],
            full_name="WrongTitle",
        )
        json_api = self.get_fake_json_api()
        self.add_fake_study_sites_response()
        study_sites = get_study_sites(json_api=json_api)
        audit_results = audit_drupal_study_sites(
            study_sites=study_sites, should_update=True
        )
        assert audit_results.encountered_issues() is False
        assert audit_results.count_new_rows() == 1
        assert audit_results.count_update_rows() == 1
        assert StudySite.objects.all().count() == 2
        first_test_ss = StudySite.objects.get(
            short_name=TEST_STUDY_SITE_DATA[0]["title"]
        )
        # did we update the long name
        assert first_test_ss.full_name == TEST_STUDY_SITE_DATA[0]["field_long_name"]

    @responses.activate
    def test_audit_study_sites_with_extra_site(self):
        StudySite.objects.create(
            drupal_node_id=99, short_name="ExtraSite", full_name="ExtraSiteLong"
        )
        json_api = self.get_fake_json_api()
        self.add_fake_study_sites_response()
        study_sites = get_study_sites(json_api=json_api)
        audit_results = audit_drupal_study_sites(
            study_sites=study_sites, should_update=True
        )
        assert audit_results.encountered_issues() is True
