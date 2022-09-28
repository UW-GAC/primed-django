from factory import Faker, Sequence
from factory.django import DjangoModelFactory

from .. import models


class StudyFactory(DjangoModelFactory):
    """A factory for the Study model."""

    short_name = Faker("word")
    full_name = Faker("company")

    class Meta:
        model = models.Study
        django_get_or_create = ["short_name"]


class DataUsePermissionFactory(DjangoModelFactory):
    """A factory for the MainConsent model."""

    code = Faker("word")
    description = Faker("catch_phrase")
    identifier = Sequence(lambda n: "DUO:{0:07d}".format(n))

    class Meta:
        model = models.DataUsePermission


class DataUseModifierFactory(DjangoModelFactory):
    """A factory for the ConsentModifier model."""

    code = Faker("word")
    description = Faker("catch_phrase")
    identifier = Sequence(lambda n: "DUO:{0:07d}".format(n))

    class Meta:
        model = models.DataUseModifier
