# from anvil_consortium_manager.tests.factories import ManagedGroupFactory
# from factory import Faker, Sequence, SubFactory
# from factory.django import DjangoModelFactory
# from factory.fuzzy import FuzzyChoice
#
# from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
# from primed.users.tests.factories import UserFactory
#
# from .. import models
#
#
# # class AgreementVersionFactory(DjangoModelFactory):
# #     """A factory for the AgreementVersion model."""
# #
# #     major_version = Sequence(lambda n: n)
# #     minor_version = 0
# # class SignedAgreementFactory(DjangoModelFactory):
# #     """A factory for the SignedAgreement model."""
# #
# #     cc_id = Sequence(lambda n: n + 1001)
# #     representative = SubFactory(UserFactory)
# #     representative_role = Faker("job")
# #     institution = Faker("company")
# #     type = FuzzyChoice(
# #         models.SignedAgreement.TYPE_CHOICES,
# #         getter=lambda c: c[0],
# #     )
# #     version = Faker("random_int")
# #     date_last_signed = Faker("date")
# #     anvil_access_group = SubFactory(ManagedGroupFactory)
# #
# #     class Meta:
# #         model = models.SignedAgreement
# #
# #
# # class MemberAgreementFactory(DjangoModelFactory):
# #
# #     signed_agreement = SubFactory(
# #         SignedAgreementFactory, type=models.SignedAgreement.MEMBER
# #     )
# #     study_site = SubFactory(StudySiteFactory)
# #
# #     class Meta:
# #         model = models.MemberAgreement
# #
# #
# # class MemberComponentAgreementFactory(DjangoModelFactory):
# #
# #     signed_agreement = SubFactory(
# #         SignedAgreementFactory, type=models.SignedAgreement.MEMBER_COMPONENT
# #     )
# #     component_of = SubFactory(MemberAgreementFactory)
# #
# #     class Meta:
# #         model = models.MemberComponentAgreement
# #
# #
# # class DataAffiliateAgreementFactory(DjangoModelFactory):
# #
# #     signed_agreement = SubFactory(
# #         SignedAgreementFactory, type=models.SignedAgreement.DATA_AFFILIATE
# #     )
# #     study = SubFactory(StudyFactory)
# #
# #     class Meta:
# #         model = models.DataAffiliateAgreement
# #
# #
# # class DataAffiliateComponentAgreementFactory(DjangoModelFactory):
# #
# #     signed_agreement = SubFactory(
# #         SignedAgreementFactory, type=models.SignedAgreement.DATA_AFFILIATE_COMPONENT
# #     )
# #     component_of = SubFactory(DataAffiliateAgreementFactory)
# #
# #     class Meta:
# #         model = models.DataAffiliateComponentAgreement
# #
# #
# # class NonDataAffiliateAgreementFactory(DjangoModelFactory):
# #
# #     signed_agreement = SubFactory(
# #         SignedAgreementFactory, type=models.SignedAgreement.NON_DATA_AFFILIATE
# #     )
# #     affiliation = Faker("company")
# #
# #     class Meta:
# #         model = models.NonDataAffiliateAgreement
# #
# #
# # class NonDataAffiliateComponentAgreementFactory(DjangoModelFactory):
# #
# #     signed_agreement = SubFactory(
# #         SignedAgreementFactory, type=models.SignedAgreement.NON_DATA_AFFILIATE_COMPONENT
# #     )
# #     component_of = SubFactory(NonDataAffiliateAgreementFactory)
# #
# #     class Meta:
# #         model = models.NonDataAffiliateComponentAgreement
