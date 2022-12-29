from django.contrib import admin

from . import models

# TODO: use a tree admin somehow


class DUOAdmin(admin.ModelAdmin):
    """Admin class for DUO models."""

    list_display = (
        "term",
        "abbreviation",
        "identifier",
        "parent",
    )
    search_fields = (
        "term",
        "abbreviation",
        "definition",
    )


admin.site.register(models.DataUsePermission, DUOAdmin)
admin.site.register(models.DataUseModifier, DUOAdmin)
