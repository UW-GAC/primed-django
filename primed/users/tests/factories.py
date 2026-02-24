from typing import Any, Sequence

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from factory import Faker, post_generation
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    username = Faker("user_name")
    email = Faker("email")
    name = Faker("name")

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):
        password = (
            extracted
            if extracted
            else Faker(
                "password",
                length=42,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ).evaluate(None, None, extra={"locale": None})
        )
        self.set_password(password)
        self.save()

    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]
        skip_postgeneration_save = True

    @post_generation
    def study_sites(self, create, extracted, **kwargs):
        if not create or not extracted:
            # Simple build, or nothing to add, do nothing.
            return

        print(extracted)
        # Add the iterable of groups using bulk addition
        # self.study_sites.add(*extracted)


class GroupFactory(DjangoModelFactory):
    name = Faker("name")

    class Meta:
        model = Group
