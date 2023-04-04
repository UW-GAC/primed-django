from anvil_consortium_manager.tests.factories import ManagedGroupFactory
from factory import Faker, Sequence, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from primed.users.tests.factories import UserFactory

from .. import models


class SignedAgreementFactory(DjangoModelFactory):
    """A factory for the SignedAgreement model."""

    cc_id = Sequence(lambda n: n + 1001)
    representative = SubFactory(UserFactory)
    representative_role = Faker("job")
    institution = Faker("company")
    type = FuzzyChoice(
        models.SignedAgreement.TYPE_CHOICES,
        getter=lambda c: c[0],
    )
    version = Faker("random_int")
    date_last_signed = Faker("date")
    anvil_access_group = SubFactory(ManagedGroupFactory)

    class Meta:
        model = models.SignedAgreement
