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


class UserDataAuditResults:
    def __init__(self, results):
        self.results = results

    ISSUE_RESULT_TYPE = "issue"
    NEW_RESULT_TYPE = "new"
    UPDATE_RESULT_TYPE = "update"

    def encountered_issues(self):
        for row in self.results:
            if row["result_type"] == self.ISSUE_RESULT_TYPE:
                return True
        return False

    def count_new_rows(self):
        new_count = 0
        for row in self.results:
            if row["result_type"] == self.NEW_RESULT_TYPE:
                new_count += 1
        return new_count

    def count_update_rows(self):
        update_count = 0
        for row in self.results:
            if row["result_type"] == self.UPDATE_RESULT_TYPE:
                update_count += 1
        return update_count


def get_drupal_json_api():

    json_api_client_id = settings.DRUPAL_API_CLIENT_ID
    json_api_client_secret = settings.DRUPAL_API_CLIENT_SECRET

    token_url = f"{settings.DRUPAL_SITE_URL}/oauth/token"
    client = BackendApplicationClient(client_id=json_api_client_id)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(
        token_url=token_url,
        client_id=json_api_client_id,
        client_secret=json_api_client_secret,
    )

    drupal_api = jsonapi_requests.Api.config(
        {
            "API_ROOT": f"{settings.DRUPAL_SITE_URL}/jsonapi",
            "AUTH": OAuth2(client=client, client_id=json_api_client_id, token=token),
            "VALIDATE_SSL": True,
        }
    )
    return drupal_api


def drupal_data_study_site_audit(should_update=False):
    json_api = get_drupal_json_api()
    study_sites = get_study_sites(json_api)
    status = audit_drupal_study_sites(
        study_sites=study_sites, should_update=should_update
    )
    # audit_drupal_users(study_sites=study_sites, should_update=should_update)
    return status


def drupal_data_user_audit(should_update=False):
    json_api = get_drupal_json_api()
    study_sites = get_study_sites(json_api=json_api)
    status = audit_drupal_users(
        study_sites=study_sites, should_update=should_update, json_api=json_api
    )
    return status


def audit_drupal_users(study_sites, json_api, should_update=False):

    issues = []

    user_endpoint_url = "user/user"
    drupal_uids = set()

    drupal_adapter = SocialAccountAdapter()
    max_users = 3
    user_count = 0
    while user_endpoint_url is not None:
        print(f"GETTING {user_endpoint_url}")
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
            else:
                print(f"No study sites for user {user.attributes['display_name']}")

            # no uid is blocked or anonymous
            if not drupal_uid:
                print(
                    f"Skipping blocked or anonymous user {user.attributes['display_name']} {user}"
                )
                # FIXME DEACTIVATE if exists in our system
                continue

            try:
                sa = SocialAccount.objects.get(
                    uid=user.attributes["drupal_internal__uid"],
                    provider=CustomProvider.id,
                )
            except ObjectDoesNotExist:
                print(
                    f"NO SA found for user {user.attributes['drupal_internal__uid']} {user}"
                )
                drupal_user = get_user_model()()
                drupal_user.username = drupal_username
                drupal_user.email = drupal_email
                drupal_user.save()
                sa = SocialAccount.objects.create(
                    user=drupal_user,
                    uid=user.attributes["drupal_internal__uid"],
                    provider=CustomProvider.id,
                )
            else:
                print(f"Found {sa} for {user}")
                user_changed = drupal_adapter.update_user_info(
                    user=sa.user,
                    extra_data={
                        "preferred_username": drupal_username,
                        "first_name": drupal_firstname,
                        "last_name": drupal_lastname,
                        "email": drupal_email,
                    },
                    apply_update=should_update,
                )
                if user_changed:
                    pass
                user_sites_changed = drupal_adapter.update_user_study_sites(
                    user=sa.user,
                    extra_data={
                        "study_site_or_center": drupal_user_study_site_shortnames
                    },
                )
                if user_sites_changed:
                    pass

                drupal_uids.add(sa.user.id)
            user_count += 1
            if user_count > max_users:
                break
        if user_count > max_users:
            break

    # find active drupal users that we did not account before
    # unaudited_drupal_accounts = SocialAccount.objects.filter(
    #     provider=CustomProvider.id, user__is_active=True
    # ).exclude(uid__in=drupal_uids)
    return issues


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


def audit_drupal_study_sites(study_sites, should_update=False):

    valid_nodes = set()
    results = []

    for study_site_info in study_sites.values():

        short_name = study_site_info["short_name"]
        full_name = study_site_info["full_name"]
        node_id = study_site_info["node_id"]
        valid_nodes.add(node_id)

        try:
            study_site = StudySite.objects.get(drupal_node_id=node_id)
        except ObjectDoesNotExist:
            if should_update is True:
                study_site = StudySite.objects.create(
                    drupal_node_id=node_id, short_name=short_name, full_name=full_name
                )
            results.append(
                {
                    "result_type": "new",
                    "data_type": "study_site",
                    "data": study_site_info,
                }
            )
        else:
            if study_site.full_name != full_name or study_site.short_name != short_name:
                study_site.full_name = full_name
                study_site.short_name = short_name
                if should_update is True:
                    study_site.save()
                results.append(
                    {
                        "result_type": "update",
                        "data_type": "study_site",
                        "data": study_site_info,
                    }
                )

    invalid_study_sites = StudySite.objects.exclude(drupal_node_id__in=valid_nodes)

    for iss in invalid_study_sites:
        results.append(
            {
                "result_type": "issue",
                "issue_type": "invalid_site",
                "data_type": "study_site",
                "data": iss,
            }
        )

    return UserDataAuditResults(results)
