# class DataUsePermissionFactory(DjangoModelFactory):
#     """A factory for the MainConsent model."""
#
#     code = Sequence(lambda n: "code{}".format(n))
#     description = Faker("catch_phrase")
#     identifier = Sequence(lambda n: "DUO:{0:07d}".format(n))
#
#     class Meta:
#         model = models.DataUsePermission
#         django_get_or_create = ("code",)
#
#
# class DataUseModifierFactory(DjangoModelFactory):
#     """A factory for the ConsentModifier model."""
#
#     code = Sequence(lambda n: "code{}".format(n))
#     description = Faker("catch_phrase")
#     identifier = Sequence(lambda n: "DUO:{0:07d}".format(n))
#
#     class Meta:
#         model = models.DataUseModifier
#
#
# class DataUseOntologyModelFactory(DjangoModelFactory):
#     """A factory for the StudyConsentGroup model."""
#
#     data_use_permission = SubFactory(DataUsePermissionFactory)
#     data_use_limitations = Faker("paragraph", nb_sentences=3)
#
#     # Handle many-to-many relationships as recommended by factoryboy.
#     @post_generation
#     def data_use_modifiers(self, create, extracted, **kwargs):
#         if not create:
#             # Simple build, do nothing.
#             return
#         if extracted:
#             # A list of data_use_modifiers were passed in, use them.
#             for modifier in extracted:
#                 self.data_use_modifiers.add(modifier)
#
#     class Meta:
#         model = models.DataUseOntologyModel
#         abstract = True
