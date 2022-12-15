from django.urls import include, path

from . import views

app_name = "dbgap"

dbgap_study_accession_patterns = (
    [
        path("", views.dbGaPStudyAccessionList.as_view(), name="list"),
        path("new/", views.dbGaPStudyAccessionCreate.as_view(), name="new"),
        path(
            "<int:dbgap_phs>", views.dbGaPStudyAccessionDetail.as_view(), name="detail"
        ),
    ],
    "dbgap_study_accessions",
)

data_access_request_patterns = (
    [
        path(
            "new/",
            views.dbGaPDataAccessSnapshotCreate.as_view(),
            name="new",
        ),
        path(
            "<int:dbgap_data_access_snapshot_pk>/",
            views.dbGaPDataAccessSnapshotDetail.as_view(),
            name="detail",
        ),
        path(
            "<int:dbgap_data_access_snapshot_pk>/audit/",
            views.dbGaPDataAccessSnapshotAudit.as_view(),
            name="audit",
        ),
    ],
    "dbgap_data_access_snapshots",
)

dbgap_application_patterns = (
    [
        path("", views.dbGaPApplicationList.as_view(), name="list"),
        path("new/", views.dbGaPApplicationCreate.as_view(), name="new"),
        path(
            "update_dars/",
            views.dbGaPDataAccessSnapshotCreateMultiple.as_view(),
            name="update_dars",
        ),
        path(
            "<int:dbgap_project_id>/",
            views.dbGaPApplicationDetail.as_view(),
            name="detail",
        ),
        path("<int:dbgap_project_id>/dars/", include(data_access_request_patterns)),
    ],
    "dbgap_applications",
)


urlpatterns = [
    path("studies/", include(dbgap_study_accession_patterns)),
    path("applications/", include(dbgap_application_patterns)),
]
