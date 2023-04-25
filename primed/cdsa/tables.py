"""Tables for the `cdsa` app."""

import django_tables2 as tables

from . import models


class SignedAgreementTable(tables.Table):

    cc_id = tables.Column(linkify=True)
    representative = tables.Column(linkify=True)
    representative_role = tables.Column(verbose_name="Role")
    combined_type = tables.Column(order_by=("type", "-is_primary"))
    number_accessors = tables.Column(
        verbose_name="Number of accessors",
        accessor="anvil_access_group__groupaccountmembership_set__count",
    )

    class Meta:
        model = models.SignedAgreement
        fields = (
            "cc_id",
            "representative",
            "representative_role",
            "signing_institution",
            "combined_type",
            "version",
            "date_signed",
            "number_accessors",
        )
