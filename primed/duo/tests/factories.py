import factory

from .. import models


class DUOFactory(factory.django.DjangoModelFactory):
    """Abstract factory definition DUO fields."""

    class Meta:
        abstract = True

    identifier = factory.Sequence(lambda n: "DUO:{0:07d}".format(n))
    abbreviation = factory.Sequence(lambda n: "perm{}".format(n))
    term = factory.Faker("catch_phrase")
    definition = factory.Faker("paragraph")


class DataUsePermissionFactory(DUOFactory):
    """A factory for the MainConsent model."""

    class Meta:
        model = models.DataUsePermission

    pass


class DataUseModifierFactory(DUOFactory):
    """A factory for the DataUseModifier model."""

    class Meta:
        model = models.DataUseModifier

    pass


class DataUseOntologyModelFactory(factory.django.DjangoModelFactory):
    """A factory for the StudyConsentGroup model."""

    data_use_permission = factory.SubFactory(DataUsePermissionFactory)
    data_use_limitations = factory.Faker("paragraph", nb_sentences=3)

    # Handle many-to-many relationships as recommended by factoryboy.
    @factory.post_generation
    def data_use_modifiers(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return
        if extracted:
            # A list of data_use_modifiers were passed in, use them.
            for modifier in extracted:
                self.data_use_modifiers.add(modifier)

    class Meta:
        model = models.DataUseOntologyModel
        abstract = True
