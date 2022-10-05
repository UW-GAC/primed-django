from django.urls import include, path

from . import views

app_name = "dbgap"


dbgap_study_accession_patterns = (
    [
        path("", views.dbGaPStudyAccessionList.as_view(), name="list"),
        path("new/", views.dbGaPStudyAccessionCreate.as_view(), name="new"),
        path("<int:pk>", views.dbGaPStudyAccessionDetail.as_view(), name="detail"),
    ],
    "dbgap_study_accessions",
)

data_access_request_patterns = (
    [
        path(
            "new/",
            views.dbGaPDataAccessRequestCreateFromJson.as_view(),
            name="new_from_json",
        ),
    ],
    "dbgap_data_access_requests",
)

dbgap_application_patterns = (
    [
        path("", views.dbGaPApplicationList.as_view(), name="list"),
        path("new/", views.dbGaPApplicationCreate.as_view(), name="new"),
        path("<int:pk>/", views.dbGaPApplicationDetail.as_view(), name="detail"),
        path("<int:dbgap_application_pk>/dars/", include(data_access_request_patterns)),
    ],
    "dbgap_applications",
)

urlpatterns = [
    path("studies/", include(dbgap_study_accession_patterns)),
    path("applications/", include(dbgap_application_patterns)),
]
