from django.urls import include, path

from . import views

app_name = "cdsa"

member_agreement_patterns = (
    [
        path("", views.MemberAgreementList.as_view(), name="list"),
        path("new/", views.MemberAgreementCreate.as_view(), name="new"),
        path("<int:cc_id>/", views.MemberAgreementDetail.as_view(), name="detail"),
    ],
    "members",
)

data_affiliate_agreement_patterns = (
    [
        path("", views.DataAffiliateAgreementList.as_view(), name="list"),
        path("new/", views.DataAffiliateAgreementCreate.as_view(), name="new"),
        path(
            "<int:cc_id>/", views.DataAffiliateAgreementDetail.as_view(), name="detail"
        ),
    ],
    "data_affiliates",
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
    ],
    "non_data_affiliates",
)

agreement_patterns = (
    [
        path("", views.SignedAgreementList.as_view(), name="list"),
        path("members/", include(member_agreement_patterns)),
        path("data_affiliates/", include(data_affiliate_agreement_patterns)),
        path("non_data_affiliates/", include(non_data_affiliate_agreement_patterns)),
    ],
    "agreements",
)

audit_patterns = (
    [
        path("agreements/", views.SignedAgreementAudit.as_view(), name="agreements"),
        path("workspaces/", views.CDSAWorkspaceAudit.as_view(), name="workspaces"),
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
    path("agreements/", include(agreement_patterns)),
    path("records/", include(records_patterns)),
    path("audit/", include(audit_patterns)),
]
