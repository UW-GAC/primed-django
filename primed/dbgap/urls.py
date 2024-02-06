from django.urls import include, path

from . import views

app_name = "dbgap"

dbgap_study_accession_patterns = (
    [
        path("", views.dbGaPStudyAccessionList.as_view(), name="list"),
        path("new/", views.dbGaPStudyAccessionCreate.as_view(), name="new"),
        path(
            "autocomplete/",
            views.dbGaPStudyAccessionAutocomplete.as_view(),
            name="autocomplete",
        ),
        path(
            "<int:dbgap_phs>", views.dbGaPStudyAccessionDetail.as_view(), name="detail"
        ),
        path(
            "<int:dbgap_phs>/update/",
            views.dbGaPStudyAccessionUpdate.as_view(),
            name="update",
        ),
    ],
    "dbgap_study_accessions",
)

data_access_snapshot_patterns = (
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
    ],
    "dbgap_data_access_snapshots",
)

data_access_request_patterns = (
    [
        path("current/", views.dbGaPDataAccessRequestList.as_view(), name="current"),
        path(
            "history/<int:dbgap_dar_id>",
            views.dbGaPDataAccessRequestHistory.as_view(),
            name="history",
        ),
    ],
    "dars",
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
        # path("dars/", views.dbGaPDataAccessRequestList.as_view(), name="dars"),
        path(
            "<int:dbgap_project_id>/",
            views.dbGaPApplicationDetail.as_view(),
            name="detail",
        ),
        path("<int:dbgap_project_id>/dars/", include(data_access_snapshot_patterns)),
        path(
            "<int:dbgap_project_id>/audit/",
            views.dbGaPApplicationAudit.as_view(),
            name="audit",
        ),
    ],
    "dbgap_applications",
)

dbgap_workspace_patterns = (
    [
        path(
            "<slug:billing_project_slug>/<slug:workspace_slug>/audit/",
            views.dbGaPWorkspaceAudit.as_view(),
            name="audit",
        ),
    ],
    "workspaces",
)

records_patterns = (
    [
        path("", views.dbGaPRecordsIndex.as_view(), name="index"),
        path(
            "applications/",
            views.dbGaPApplicationRecords.as_view(),
            name="applications",
        ),
    ],
    "records",
)


urlpatterns = [
    path("applications/", include(dbgap_application_patterns)),
    path("audit/", views.dbGaPAudit.as_view(), name="audit"),
    path("dars/", include(data_access_request_patterns)),
    path("records/", include(records_patterns)),
    path("studies/", include(dbgap_study_accession_patterns)),
    path("workspaces/", include(dbgap_workspace_patterns)),
]
