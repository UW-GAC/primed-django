from factory import Faker
from factory.django import DjangoModelFactory

from .. import models


class StudySiteFactory(DjangoModelFactory):
    """A factory for the StudySite model."""

    short_name = Faker("word")
    full_name = Faker("company")

    class Meta:
        model = models.StudySite
        django_get_or_create = ["short_name"]


class StudyFactory(DjangoModelFactory):
    """A factory for the Study model."""

    short_name = Faker("word")
    full_name = Faker("company")

    class Meta:
        model = models.Study
        django_get_or_create = ["short_name"]
