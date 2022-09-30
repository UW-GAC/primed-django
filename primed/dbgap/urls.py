from django.urls import include, path

from . import views

app_name = "dbgap"


dbgap_study_patterns = (
    [
        path("<int:pk>", views.dbGaPStudyDetail.as_view(), name="detail"),
    ],
    "dbgap_studies",
)

urlpatterns = [
    path("studies/", include(dbgap_study_patterns)),
]
