from django.urls import include, path

from . import views

app_name = "primed_anvil"


study_patterns = (
    [
        path("<int:pk>", views.StudyDetail.as_view(), name="detail"),
    ],
    "studies",
)

urlpatterns = [
    path("studies/", include(study_patterns)),
]
