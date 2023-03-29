from django.urls import include, path

from . import views

app_name = "cdsa"


agreement_patterns = (
    [
        # path("", views.dbGaPApplicationList.as_view(), name="list"),
        path("new/", views.CDSACreate.as_view(), name="new"),
        #     path(
        #         "update_dars/",
        #         views.dbGaPDataAccessSnapshotCreateMultiple.as_view(),
        #         name="update_dars",
        #     ),
        #     path(
        #         "<int:dbgap_project_id>/",
        #         views.dbGaPApplicationDetail.as_view(),
        #         name="detail",
        #     ),
        #     path("<int:dbgap_project_id>/dars/", include(data_access_request_patterns)),
        #     path(
        #         "<int:dbgap_project_id>/audit/",
        #         views.dbGaPApplicationAudit.as_view(),
        #         name="audit",
        #     ),
    ],
    "agreements",
)

urlpatterns = [
    path("agreements/", include(agreement_patterns)),
]
