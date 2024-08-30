from factory import Faker, Sequence
from factory.django import DjangoModelFactory

from .. import models


class StudyFactory(DjangoModelFactory):
    """A factory for the Study model."""

    short_name = Sequence(lambda n: "Study:{0:07d}".format(n))
    full_name = Faker("company")

    class Meta:
        model = models.Study


class StudySiteFactory(DjangoModelFactory):
    """A factory for the StudySite model."""

    short_name = Sequence(lambda n: "Site:{0:07d}".format(n))
    full_name = Faker("company")

    class Meta:
        model = models.StudySite


class AvailableDataFactory(DjangoModelFactory):
    """A factory for the AvailableData model."""

    class Meta:
        model = models.AvailableData

    name = Sequence(lambda n: "data:{0:07d}".format(n))
    description = Faker("paragraph")
