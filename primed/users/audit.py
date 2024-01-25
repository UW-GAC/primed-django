import logging

import jsonapi_requests
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2, OAuth2Session

from primed.drupal_oauth_provider.provider import CustomProvider
from primed.primed_anvil.models import StudySite
from primed.users.adapters import SocialAccountAdapter

logger = logging.getLogger(__name__)


class AuditResults:
    def __init__(self):
        self.results = []
        self.data_type = None

    # Data from api was not able to be handled
    RESULT_TYPE_ISSUE = "issue"
    # A new record was created during audit
    RESULT_TYPE_NEW = "new"
    # An existing record was updated
    RESULT_TYPE_UPDATE = "update"
    # A record was removed or deactivated
    RESULT_TYPE_REMOVAL = "removed"

    def add_new(self, data):
        self.results.append(
            {
                "data_type": self.data_type,
                "result_type": self.RESULT_TYPE_NEW,
                "data": data,
            }
        )

    def add_update(self, data):
        self.results.append(
            {
                "data_type": self.data_type,
                "result_type": self.RESULT_TYPE_UPDATE,
                "data": data,
            }
        )

    def add_issue(self, data):
        self.results.append(
            {
                "data_type": self.data_type,
                "result_type": self.RESULT_TYPE_ISSUE,
                "data": data,
            }
        )

    def add_removal(self, data):
        self.results.append(
            {
                "data_type": self.data_type,
                "result_type": self.RESULT_TYPE_REMOVAL,
                "data": data,
            }
        )

    def rows_by_result_type(self, result_type):
        found = []
        for row in self.results:
            if row["result_type"] == result_type:
                found.append(row)
        return found

    def row_count_by_result_type(self, result_type):
        return len(self.rows_by_result_type(result_type))

    def count_new_rows(self):
        return self.row_count_by_result_type(self.RESULT_TYPE_NEW)

    def count_update_rows(self):
        return self.row_count_by_result_type(self.RESULT_TYPE_UPDATE)

    def count_removal_rows(self):
        return self.row_count_by_result_type(self.RESULT_TYPE_REMOVAL)

    def count_issue_rows(self):
        return self.row_count_by_result_type(self.RESULT_TYPE_ISSUE)

    def encountered_issues(self):
        return self.count_issue_rows() > 0

    def __str__(self) -> str:
        return (
            f"Audit for {self.data_type} "
            f"Issues: {self.count_issue_rows()} "
            f"New: {self.count_new_rows()} "
            f"Updates: {self.count_update_rows()} "
            f"Removals: {self.count_removal_rows()}"
        )


class UserAuditResults(AuditResults):
    def __init__(self):
        super().__init__()
        self.data_type = "user"


class SiteAuditResults(AuditResults):
    def __init__(self):
        super().__init__()
        self.data_type = "site"


def get_drupal_json_api():

    json_api_client_id = settings.DRUPAL_API_CLIENT_ID
    json_api_client_secret = settings.DRUPAL_API_CLIENT_SECRET

    token_url = f"{settings.DRUPAL_SITE_URL}/oauth/token"
    client = BackendApplicationClient(client_id=json_api_client_id)
    oauth = OAuth2Session(client=client)
    api_root = f"{settings.DRUPAL_SITE_URL}/{settings.DRUPAL_API_REL_PATH}"

    token = oauth.fetch_token(
        token_url=token_url,
        client_id=json_api_client_id,
        client_secret=json_api_client_secret,
    )

    drupal_api = jsonapi_requests.Api.config(
        {
            "API_ROOT": api_root,
            "AUTH": OAuth2(client=client, client_id=json_api_client_id, token=token),
            "VALIDATE_SSL": True,
        }
    )
    return drupal_api


def drupal_data_study_site_audit(apply_changes=False):
    json_api = get_drupal_json_api()
    study_sites = get_study_sites(json_api)
    status = audit_drupal_study_sites(
        study_sites=study_sites, apply_changes=apply_changes
    )

    return status


def drupal_data_user_audit(apply_changes=False):
    json_api = get_drupal_json_api()
    study_sites = get_study_sites(json_api=json_api)
    status = audit_drupal_users(
        study_sites=study_sites, apply_changes=apply_changes, json_api=json_api
    )
    return status


def audit_drupal_users(study_sites, json_api, apply_changes=False):

    audit_results = UserAuditResults()

    user_endpoint_url = "user/user"
    drupal_uids = set()

    drupal_adapter = SocialAccountAdapter()

    user_count = 0
    while user_endpoint_url is not None:

        users_endpoint = json_api.endpoint(user_endpoint_url)
        users_endpoint_response = users_endpoint.get()

        # If there are more, there will be a 'next' link
        next_user_endpoint = users_endpoint_response.content.links.get("next")
        if next_user_endpoint:
            user_endpoint_url = next_user_endpoint["href"]
        else:
            user_endpoint_url = None

        for user in users_endpoint_response.data:
            drupal_uid = user.attributes.get("drupal_internal__uid")
            drupal_username = user.attributes.get("name")
            drupal_email = user.attributes.get("mail")
            drupal_firstname = user.attributes.get("field_given_first_name_s_")
            drupal_lastname = user.attributes.get("field_examples_family_last_name_")
            drupal_full_name = " ".join(
                part for part in (drupal_firstname, drupal_lastname) if part
            )
            drupal_study_sites_rel = user.relationships.get(
                "field_study_site_or_center"
            )
            drupal_user_study_site_shortnames = []
            if drupal_study_sites_rel:
                for dss in drupal_study_sites_rel.data:
                    study_site_uuid = dss.id
                    study_site_info = study_sites[study_site_uuid]

                    drupal_user_study_site_shortnames.append(
                        study_site_info["short_name"]
                    )
            is_new_user = False
            # no uid is blocked or anonymous
            if not drupal_uid:
                # FIXME - deactivate if not anonymous and present locally
                continue

            try:
                sa = SocialAccount.objects.get(
                    uid=user.attributes["drupal_internal__uid"],
                    provider=CustomProvider.id,
                )
            except ObjectDoesNotExist:
                drupal_user = get_user_model()()
                drupal_user.username = drupal_username
                drupal_user.name = drupal_full_name
                drupal_user.email = drupal_email
                drupal_user.save()
                is_new_user = True
                sa = SocialAccount.objects.create(
                    user=drupal_user,
                    uid=user.attributes["drupal_internal__uid"],
                    provider=CustomProvider.id,
                )
                audit_results.add_new(data=user)

            user_changed = drupal_adapter.update_user_info(
                user=sa.user,
                extra_data={
                    "preferred_username": drupal_username,
                    "first_name": drupal_firstname,
                    "last_name": drupal_lastname,
                    "email": drupal_email,
                },
                apply_update=apply_changes,
            )
            logger.info(
                f"for user {user} ss_short_names {drupal_user_study_site_shortnames}"
            )

            user_sites_changed = drupal_adapter.update_user_study_sites(
                user=sa.user,
                extra_data={"study_site_or_center": drupal_user_study_site_shortnames},
            )
            if user_changed or user_sites_changed and not is_new_user:
                audit_results.add_update(data=user)

            drupal_uids.add(sa.user.id)
            user_count += 1

    # find active drupal users that we did not account before
    # unaudited_drupal_accounts = SocialAccount.objects.filter(
    #     provider=CustomProvider.id, user__is_active=True
    # ).exclude(uid__in=drupal_uids)
    return audit_results


def get_study_sites(json_api):
    study_sites_endpoint = json_api.endpoint("node/study_site_or_center")
    study_sites_response = study_sites_endpoint.get()
    study_sites_info = dict()

    for ss in study_sites_response.data:
        short_name = ss.attributes["title"]
        full_name = ss.attributes["field_long_name"]
        node_id = ss.attributes["drupal_internal__nid"]

        study_sites_info[ss.id] = {
            "node_id": node_id,
            "short_name": short_name,
            "full_name": full_name,
        }
    return study_sites_info


def audit_drupal_study_sites(study_sites, apply_changes=False):

    valid_nodes = set()
    audit_results = SiteAuditResults()

    for study_site_info in study_sites.values():

        short_name = study_site_info["short_name"]
        full_name = study_site_info["full_name"]
        node_id = study_site_info["node_id"]
        valid_nodes.add(node_id)

        try:
            study_site = StudySite.objects.get(drupal_node_id=node_id)
        except ObjectDoesNotExist:
            if apply_changes is True:
                study_site = StudySite.objects.create(
                    drupal_node_id=node_id, short_name=short_name, full_name=full_name
                )
            audit_results.add_new(data=study_site_info)
        else:
            if study_site.full_name != full_name or study_site.short_name != short_name:
                study_site.full_name = full_name
                study_site.short_name = short_name
                if apply_changes is True:
                    study_site.save()
                audit_results.add_update(data=study_site_info)

    invalid_study_sites = StudySite.objects.exclude(drupal_node_id__in=valid_nodes)

    for iss in invalid_study_sites:
        audit_results.add_issue(data=iss)

    return audit_results
