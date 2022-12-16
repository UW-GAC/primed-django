# from django.db import models

# Create your models here.
# class DataUsePermission(TimeStampedModel, models.Model):
#     """A model to track the allowed main consent codes using GA4GH DUO codes."""
#
#     code = models.CharField(
#         max_length=15,
#         unique=True,
#         help_text="""The short code for this consent group (e.g., GRU).""",
#     )
#     description = models.CharField(
#         max_length=255,
#         unique=True,
#         help_text="""The description for this consent group (e.g., General Research Use).""",
#     )
#     identifier = models.CharField(
#         max_length=31,
#         unique=True,
#         help_text="""The identifier of this consent group (e.g., DUO:0000045).""",
#     )
#     requires_disease_restriction = models.BooleanField(
#         default=False,
#         help_text="Indicator of whether an additional disease restriction is required for this term.",
#     )
#     history = HistoricalRecords()
#
#     def __str__(self):
#         """String method.
#         Returns:
#             A string showing the short consent code of the object.
#         """
#         return self.code
#
#
# class DataUseModifier(TimeStampedModel, models.Model):
#     """A model to track the allowed consent modifiers using GA4GH DUO codes."""
#
#     code = models.CharField(
#         max_length=15,
#         unique=True,
#         help_text="""The short code for this modifier (e.g., NPU).""",
#     )
#     description = models.CharField(
#         max_length=255,
#         unique=True,
#         help_text="""The description of this modifier (e.g., Non-Profit Use only).""",
#     )
#     identifier = models.CharField(
#         max_length=31,
#         unique=True,
#         help_text="""The identifier of this modifier (e.g., DUO:0000045).""",
#     )
#     history = HistoricalRecords()
#
#     def __str__(self):
#         """String method.
#         Returns:
#             A string showing the short consent code of the object.
#         """
#         return self.code
#
#
# class DataUseOntologyModel(models.Model):
#     """An abstract model to track a group using Data Use Ontology terms to describe allowed data use."""
#
#     data_use_permission = models.ForeignKey(
#         DataUsePermission,
#         on_delete=models.PROTECT,
#         help_text="""The DataUsePermission associated with this study-consent group.""",
#     )
#     data_use_modifiers = models.ManyToManyField(
#         DataUseModifier,
#         blank=True,
#         help_text="""The DataUseModifiers associated with this study-consent group.""",
#     )
#     disease_restriction = models.CharField(
#         max_length=255,
#         blank=True,
#         null=True,
#         help_text="The disease restriction if required by data_use_permission.",
#     )
#
#     class Meta:
#         abstract = True
#
#     def clean(self):
#         """Ensure that the disease_restriction term is set if data_use_permission requires it."""
#         # Without hasattr, we get a RelatedObjectDoesNotExist error.
#         if hasattr(self, "data_use_permission"):
#             if (
#                 self.data_use_permission.requires_disease_restriction
#                 and not self.disease_restriction
#             ):
#                 raise ValidationError(
#                     "`disease_restriction` must not be None "
#                     "because data_use_permission requires a disease restriction."
#                 )
#             if (
#                 not self.data_use_permission.requires_disease_restriction
#                 and self.disease_restriction
#             ):
#                 raise ValidationError(
#                     (
#                         "`disease_restriction` must be None "
#                         "because data_use_permission does not require a disease restriction."
#                     )
#                 )
