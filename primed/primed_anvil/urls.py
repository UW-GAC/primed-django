from django.urls import include, path

from . import views

app_name = "primed_anvil"

study_site_patterns = (
    [
        path("<int:pk>", views.StudySiteDetail.as_view(), name="detail"),
        path("", views.StudySiteList.as_view(), name="list"),
    ],
    "study_sites",
)

study_patterns = (
    [
        path("", views.StudyList.as_view(), name="list"),
        path("new/", views.StudyCreate.as_view(), name="new"),
        path("<int:pk>", views.StudyDetail.as_view(), name="detail"),
        path("autocomplete/", views.StudyAutocomplete.as_view(), name="autocomplete"),
    ],
    "studies",
)

urlpatterns = [
    path("studies/", include(study_patterns)),
    path("study_sites/", include(study_site_patterns)),
]
