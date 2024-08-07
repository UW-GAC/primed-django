from django.urls import include, path

from . import views

app_name = "primed_anvil"

study_site_patterns = (
    [
        path("<int:pk>/", views.StudySiteDetail.as_view(), name="detail"),
        path("", views.StudySiteList.as_view(), name="list"),
    ],
    "study_sites",
)

study_patterns = (
    [
        path("", views.StudyList.as_view(), name="list"),
        path("new/", views.StudyCreate.as_view(), name="new"),
        path("<int:pk>/", views.StudyDetail.as_view(), name="detail"),
        path("autocomplete/", views.StudyAutocomplete.as_view(), name="autocomplete"),
    ],
    "studies",
)

available_data_patterns = (
    [
        path("", views.AvailableDataList.as_view(), name="list"),
        path("<int:pk>/", views.AvailableDataDetail.as_view(), name="detail"),
    ],
    "available_data",
)

summary_patterns = (
    [
        path("data/", views.DataSummaryView.as_view(), name="data"),
    ],
    "summaries",
)

utilities_patterns = (
    [
        path(
            "inventory_inputs/",
            views.InventoryInputsView.as_view(),
            name="inventory_inputs",
        ),
    ],
    "utilities",
)

urlpatterns = [
    path("studies/", include(study_patterns)),
    path("study_sites/", include(study_site_patterns)),
    path("available_data/", include(available_data_patterns)),
    path("summaries/", include(summary_patterns)),
    path("utilities/", include(utilities_patterns)),
]
