from django.urls import include, path

from . import models, views

app_name = "cdsa"

agreement_version_patterns = (
    [
        path(
            "",
            views.AgreementVersionList.as_view(),
            name="list",
        ),
        path(
            "v<int:major_version>/",
            views.AgreementMajorVersionDetail.as_view(),
            name="major_version_detail",
        ),
        path(
            "v<int:major_version>/invalidate/",
            views.AgreementMajorVersionInvalidate.as_view(),
            name="invalidate",
        ),
        path(
            "v<int:major_version>.<int:minor_version>/",
            views.AgreementVersionDetail.as_view(),
            name="detail",
        ),
    ],
    "agreement_versions",
)

member_agreement_update_patterns = (
    [
        path(
            "status/",
            views.SignedAgreementStatusUpdate.as_view(),
            {"agreement_type": models.SignedAgreement.MEMBER},
            name="status",
        ),
        path(
            "accessors/",
            views.SignedAgreementAccessorsUpdate.as_view(),
            {"agreement_type": models.SignedAgreement.MEMBER},
            name="accessors",
        ),
    ],
    "update",
)

member_agreement_patterns = (
    [
        path("", views.MemberAgreementList.as_view(), name="list"),
        path("new/", views.MemberAgreementCreate.as_view(), name="new"),
        path("<int:cc_id>/", views.MemberAgreementDetail.as_view(), name="detail"),
        path("<int:cc_id>/update/", include(member_agreement_update_patterns)),
    ],
    "members",
)

data_affiliate_agreement_update_patterns = (
    [
        path(
            "status/",
            views.SignedAgreementStatusUpdate.as_view(),
            {"agreement_type": models.SignedAgreement.DATA_AFFILIATE},
            name="status",
        ),
        path(
            "accessors/",
            views.SignedAgreementAccessorsUpdate.as_view(),
            {"agreement_type": models.SignedAgreement.DATA_AFFILIATE},
            name="accessors",
        ),
        path(
            "uploaders/",
            views.DataAffiliateAgreementUploadersUpdate.as_view(),
            name="uploaders",
        ),
    ],
    "update",
)

data_affiliate_agreement_patterns = (
    [
        path("", views.DataAffiliateAgreementList.as_view(), name="list"),
        path("new/", views.DataAffiliateAgreementCreate.as_view(), name="new"),
        path("<int:cc_id>/", views.DataAffiliateAgreementDetail.as_view(), name="detail"),
        path("<int:cc_id>/update/", include(data_affiliate_agreement_update_patterns)),
    ],
    "data_affiliates",
)

non_data_affiliate_agreement_update_patterns = (
    [
        path(
            "status/",
            views.SignedAgreementStatusUpdate.as_view(),
            {"agreement_type": models.SignedAgreement.NON_DATA_AFFILIATE},
            name="status",
        ),
        path(
            "accessors/",
            views.SignedAgreementAccessorsUpdate.as_view(),
            {"agreement_type": models.SignedAgreement.NON_DATA_AFFILIATE},
            name="accessors",
        ),
    ],
    "update",
)

non_data_affiliate_agreement_patterns = (
    [
        path("", views.NonDataAffiliateAgreementList.as_view(), name="list"),
        path("new/", views.NonDataAffiliateAgreementCreate.as_view(), name="new"),
        path(
            "<int:cc_id>/",
            views.NonDataAffiliateAgreementDetail.as_view(),
            name="detail",
        ),
        path("<int:cc_id>/update/", include(non_data_affiliate_agreement_update_patterns)),
    ],
    "non_data_affiliates",
)

signed_agreement_patterns = (
    [
        path("", views.SignedAgreementList.as_view(), name="list"),
        path("members/", include(member_agreement_patterns)),
        path("data_affiliates/", include(data_affiliate_agreement_patterns)),
        path("non_data_affiliates/", include(non_data_affiliate_agreement_patterns)),
        # path("audit/", include(signed_agreement_audit_patterns)),
    ],
    "signed_agreements",
)

signed_agreement_sag_audit_patterns = (
    [
        path("", views.SignedAgreementAudit.as_view(), name="all"),
        path(
            "resolve/<int:cc_id>/",
            views.SignedAgreementAuditResolve.as_view(),
            name="resolve",
        ),
    ],
    "sag",
)

signed_agreement_accessor_audit_patterns = (
    [
        path("", views.AccessorAudit.as_view(), name="all"),
        path(
            "resolve/<int:cc_id>/<str:email>/",
            views.AccessorAuditResolve.as_view(),
            name="resolve",
        ),
    ],
    "accessors",
)

signed_agreement_uploader_audit_patterns = (
    [
        path("", views.UploaderAudit.as_view(), name="all"),
        path(
            "resolve/<int:cc_id>/<str:email>/",
            views.UploaderAuditResolve.as_view(),
            name="resolve",
        ),
    ],
    "uploaders",
)

signed_agreement_audit_patterns = (
    [
        path("sag/", include(signed_agreement_sag_audit_patterns)),
        path("accessors/", include(signed_agreement_accessor_audit_patterns)),
        path("uploaders/", include(signed_agreement_uploader_audit_patterns)),
    ],
    "signed_agreements",
)

workspace_audit_patterns = (
    [
        path("", views.CDSAWorkspaceAudit.as_view(), name="all"),
        path(
            "resolve/<slug:billing_project_slug>/<slug:workspace_slug>/",
            views.CDSAWorkspaceAuditResolve.as_view(),
            name="resolve",
        ),
    ],
    "workspaces",
)

audit_patterns = (
    [
        path("workspaces/", include(workspace_audit_patterns)),
        path("signed_agreements/", include(signed_agreement_audit_patterns)),
    ],
    "audit",
)

records_patterns = (
    [
        path("", views.RecordsIndex.as_view(), name="index"),
        path(
            "representatives/",
            views.RepresentativeRecords.as_view(),
            name="representatives",
        ),
        path(
            "studies/",
            views.StudyRecords.as_view(),
            name="studies",
        ),
        path(
            "users/",
            views.UserAccessRecords.as_view(),
            name="user_access",
        ),
        path(
            "workspaces/",
            views.CDSAWorkspaceRecords.as_view(),
            name="workspaces",
        ),
    ],
    "records",
)


urlpatterns = [
    path("agreement_versions/", include(agreement_version_patterns)),
    path("signed_agreements/", include(signed_agreement_patterns)),
    path("records/", include(records_patterns)),
    path("audit/", include(audit_patterns)),
]
