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


urlpatterns = [
    path("agreements/", include(agreement_patterns)),
]
