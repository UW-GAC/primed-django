import logging
from typing import Any, Dict

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.core.mail import mail_admins
from django.http import HttpRequest

from primed.primed_anvil.models import StudySite

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def update_user_info(self, user, extra_data: Dict, apply_update=True):
        drupal_username = extra_data.get("preferred_username")
        drupal_email = extra_data.get("email")
        first_name = extra_data.get("first_name")
        last_name = extra_data.get("last_name")
        full_name = " ".join(part for part in (first_name, last_name) if part)
        user_changed = False
        if user.name != full_name:
            logger.info(
                f"[SocialAccountAdatpter:update_user_name] user {user} " f"name updated from {user.name} to {full_name}"
            )
            user.name = full_name
            user_changed = True
        if user.username != drupal_username:
            logger.info(
                f"[SocialAccountAdatpter:update_user_name] user {user} "
                f"username updated from {user.username} to {drupal_username}"
            )
            user.username = drupal_username
            user_changed = True
        if user.email != drupal_email:
            logger.info(
                f"[SocialAccountAdatpter:update_user_name] user {user}"
                f" email updated from {user.email} to {drupal_email}"
            )
            user.email = drupal_email
            user_changed = True

        if user_changed is True and apply_update is True:
            user.save()
        return user_changed

    def update_user_study_sites(self, user, extra_data: Dict, apply_update=True):
        # Get list of research centers in domain table

        research_center_or_site = extra_data.get("study_site_or_center")
        user_sites_updated = False
        if research_center_or_site:
            if not isinstance(research_center_or_site, list):
                raise ImproperlyConfigured("sociallogin.extra_data.study_site_or_center should be a list")
            for rc_name in research_center_or_site:
                try:
                    rc = StudySite.objects.get(short_name=rc_name)
                except ObjectDoesNotExist:
                    logger.debug(
                        f"[SocialAccountAdatpter:update_user_study_sites] Ignoring drupal "
                        f"study_site_or_center {rc_name} - not in StudySite domain"
                    )
                    mail_admins(
                        subject="Missing StudySite",
                        message=f"Missing study site {rc_name} passed from drupal for user {user}",
                    )
                    continue
                else:
                    if not user.study_sites.filter(pk=rc.pk):
                        user_sites_updated = True
                        if apply_update is True:
                            user.study_sites.add(rc)
                            logger.info(
                                f"[SocialAccountAdatpter:update_user_study_sites] adding user "
                                f"study_sites user: {user} rc: {rc}"
                            )

            for existing_rc in user.study_sites.all():
                if existing_rc.short_name not in research_center_or_site:
                    user_sites_updated = True
                    if apply_update:
                        user.study_sites.remove(existing_rc)
                        logger.info(
                            "[SocialAccountAdatpter:update_user_study_sites] "
                            f"removing study_site {existing_rc} for user {user}"
                        )
            return user_sites_updated

    def update_user_groups(self, user, extra_data: Dict):
        managed_scope_status = extra_data.get("managed_scope_status")
        if managed_scope_status:
            added_groups = []
            removed_groups = []
            if not isinstance(managed_scope_status, dict):
                raise ImproperlyConfigured("sociallogin.extra_data.managed_scope_status should be a dict")
            else:
                for group_name, user_has_group in managed_scope_status.items():
                    user_group, was_created = Group.objects.get_or_create(name=group_name)
                    if was_created:
                        logger.debug(
                            f"[SocialAccountAdatpter:update_user_data] created mapped user group: {group_name}"
                        )
                    if user_has_group is True:
                        if user_group not in user.groups.all():
                            user.groups.add(user_group)
                            added_groups.append(user_group.name)
                    else:
                        if user_group in user.groups.all():
                            user.groups.remove(user_group)
                            removed_groups.append(user_group.name)
            if added_groups or removed_groups:
                logger.info(
                    f"[SocialAccountAdatpter:update_user_data] user: {user} updated groups: "
                    f"added {added_groups} removed: {removed_groups} "
                    f"managed_scope_status: {managed_scope_status}"
                )

    def update_user_data(self, sociallogin: Any):
        logger.debug(
            f"[SocialAccountAdatpter:update_user_data] account: {sociallogin.account} "
            f"extra_data {sociallogin.account.extra_data} "
            f"provider: {sociallogin.account.provider}"
        )

        extra_data = sociallogin.account.extra_data
        user = sociallogin.user

        self.update_user_info(user, extra_data)
        self.update_user_study_sites(user, extra_data)
        self.update_user_groups(user, extra_data)
