from django.contrib import admin

from . import models

admin.site.register(models.DataUsePermission)
admin.site.register(models.DataUseModifier)

# @admin.register(models.DataUsePermission)
# class DataUsePermissionAdmin(DraggableMPTTAdmin):
#     """Admin class for the `DataUsePermission` model."""
#
#     pass
#
#
# @admin.register(models.DataUseModifier)
# class DataUseModifierAdmin(DraggableMPTTAdmin):
#     """Admin class for the `DataUseModifier` model."""
#
#     pass


# @admin.register(models.DataUseModifier)
# class DataUseModifierAdmin(SimpleHistoryAdmin):
#     """Admin class for the `DataUseModifier` model."""
#
#     list_display = (
#         "code",
#         "identifier",
#         "description",
#     )
#     search_fields = (
#         "code",
#         "identifier",
#         "description",
#     )
#     sortable_by = (
#         "code",
#         "identifier",
#         "description",
#     )
