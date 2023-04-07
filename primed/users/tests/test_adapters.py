import pytest
from allauth.account import app_settings as account_settings
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.utils import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ImproperlyConfigured
from django.test.client import RequestFactory
from django.test.utils import override_settings

from primed.primed_anvil.tests.factories import StudySiteFactory
from primed.users.adapters import AccountAdapter, SocialAccountAdapter

from .factories import GroupFactory, UserFactory


@pytest.mark.django_db
class TestsUserSocialLoginAdapter(object):
    @override_settings(
        SOCIALACCOUNT_AUTO_SIGNUP=True,
        ACCOUNT_SIGNUP_FORM_CLASS=None,
        ACCOUNT_EMAIL_VERIFICATION=account_settings.EmailVerificationMethod.NONE,  # noqa
    )
    def test_drupal_social_login_adapter(self):
        factory = RequestFactory()
        request = factory.get("/accounts/login/callback/")
        request.user = AnonymousUser()
        SessionMiddleware(lambda request: None).process_request(request)
        MessageMiddleware(lambda request: None).process_request(request)

        User = get_user_model()
        user = User()
        old_name = "Old Name"
        setattr(user, account_settings.USER_MODEL_USERNAME_FIELD, "test")
        setattr(user, "name", "Old Name")
        setattr(user, account_settings.USER_MODEL_EMAIL_FIELD, "test@example.com")

        account = SocialAccount(
            provider="drupal_oauth_provider",
            uid="123",
            extra_data=dict(first_name="Old", last_name="Name"),
        )
        sociallogin = SocialLogin(user=user, account=account)
        complete_social_login(request, sociallogin)

        user = User.objects.get(**{account_settings.USER_MODEL_USERNAME_FIELD: "test"})
        assert SocialAccount.objects.filter(user=user, uid=account.uid).exists() is True
        assert user.name == old_name

    def test_update_user_name(self):
        adapter = SocialAccountAdapter()

        User = get_user_model()
        user = User()
        new_name = "New Name"
        setattr(user, account_settings.USER_MODEL_USERNAME_FIELD, "test")
        setattr(user, "name", "Old Name")
        setattr(user, account_settings.USER_MODEL_EMAIL_FIELD, "test@example.com")

        user.save()

        adapter.update_user_name(user, dict(first_name="New", last_name="Name"))
        assert user.name == new_name

    def test_update_user_study_sites_add(self):
        adapter = SocialAccountAdapter()
        rc1 = StudySiteFactory(short_name="rc1")

        User = get_user_model()
        user = User()
        setattr(user, account_settings.USER_MODEL_USERNAME_FIELD, "test")
        setattr(user, account_settings.USER_MODEL_EMAIL_FIELD, "test@example.com")

        user.save()

        adapter.update_user_study_sites(
            user, dict(study_site_or_center=[rc1.short_name])
        )
        assert user.study_sites.filter(pk=rc1.pk).exists()
        assert user.study_sites.all().count() == 1

    def test_update_user_study_sites_remove(self):
        adapter = SocialAccountAdapter()
        rc1 = StudySiteFactory(short_name="rc1")
        rc2 = StudySiteFactory(short_name="rc2")

        User = get_user_model()
        user = User()
        setattr(user, account_settings.USER_MODEL_USERNAME_FIELD, "test")
        setattr(user, account_settings.USER_MODEL_EMAIL_FIELD, "test@example.com")

        user.save()
        user.study_sites.add(rc1, rc2)
        assert user.study_sites.all().count() == 2

        adapter.update_user_study_sites(
            user, dict(study_site_or_center=[rc1.short_name])
        )
        assert user.study_sites.filter(pk=rc1.pk).exists()
        assert user.study_sites.all().count() == 1

    def test_update_user_study_sites_uknown(self):
        adapter = SocialAccountAdapter()
        user = UserFactory()
        adapter.update_user_study_sites(user, dict(study_site_or_center=["UNKNOWN"]))
        assert user.study_sites.all().count() == 0

    def test_update_study_sites_malformed(self):
        adapter = SocialAccountAdapter()
        user = UserFactory()
        with pytest.raises(ImproperlyConfigured):
            adapter.update_user_study_sites(user, dict(study_site_or_center="FOO"))

    def test_update_user_groups_add(self):
        adapter = SocialAccountAdapter()
        rc1 = GroupFactory(name="g1")

        User = get_user_model()
        user = User()
        setattr(user, account_settings.USER_MODEL_USERNAME_FIELD, "test")
        setattr(user, account_settings.USER_MODEL_EMAIL_FIELD, "test@example.com")

        user.save()

        adapter.update_user_groups(
            user, extra_data=dict(managed_scope_status={rc1.name: True})
        )
        assert user.groups.filter(pk=rc1.pk).exists()
        assert user.groups.all().count() == 1

    def test_update_user_groups_add_new(self):
        adapter = SocialAccountAdapter()

        User = get_user_model()
        user = User()
        setattr(user, account_settings.USER_MODEL_USERNAME_FIELD, "test")
        setattr(user, account_settings.USER_MODEL_EMAIL_FIELD, "test@example.com")

        user.save()
        new_group_name = "NEW_GROUP"
        adapter.update_user_groups(
            user, extra_data=dict(managed_scope_status={new_group_name: True})
        )
        assert user.groups.filter(name=new_group_name).exists()
        assert user.groups.all().count() == 1

    def test_update_user_groups_remove(self):
        adapter = SocialAccountAdapter()
        rc1 = GroupFactory(name="g1")
        rc2 = GroupFactory(name="g2")

        User = get_user_model()
        user = User()
        setattr(user, account_settings.USER_MODEL_USERNAME_FIELD, "test")
        setattr(user, account_settings.USER_MODEL_EMAIL_FIELD, "test@example.com")

        user.save()
        user.groups.add(rc1, rc2)
        assert user.groups.all().count() == 2

        adapter.update_user_groups(
            user,
            extra_data=dict(managed_scope_status={rc1.name: True, rc2.name: False}),
        )
        assert user.groups.filter(pk=rc1.pk).exists()
        assert not user.groups.filter(pk=rc2.pk).exists()
        assert user.groups.all().count() == 1

    def test_update_user_groups_malformed(self):
        adapter = SocialAccountAdapter()
        user = UserFactory()
        with pytest.raises(ImproperlyConfigured):
            adapter.update_user_groups(user, dict(managed_scope_status="FOO"))

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=True)
    def test_account_is_open_for_signup(self):
        request = RequestFactory()
        adapter = AccountAdapter()
        assert adapter.is_open_for_signup(request) is True

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=False)
    def test_account_is_not_open_for_signup(self):
        request = RequestFactory()
        adapter = AccountAdapter()
        assert adapter.is_open_for_signup(request) is False
