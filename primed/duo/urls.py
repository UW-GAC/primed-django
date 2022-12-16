from django.urls import include, path

from . import views

app_name = "duo"

data_use_permission_patterns = (
    [
        path("", views.DataUsePermissionList.as_view(), name="list"),
    ],
    "data_use_permissions",
)

data_use_modifier_patterns = (
    [
        path("", views.DataUseModifierList.as_view(), name="list"),
    ],
    "data_use_modifiers",
)

urlpatterns = [
    path("data_use_permissions/", include(data_use_permission_patterns)),
    path("data_use_modifiers/", include(data_use_modifier_patterns)),
]
