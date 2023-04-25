"""Tables for the `cdsa` app."""

import django_tables2 as tables

from . import models


class SignedAgreementTable(tables.Table):

    cc_id = tables.Column(linkify=True)
    representative = tables.Column(linkify=True)

    class Meta:
        model = models.SignedAgreement
        fields = (
            "cc_id",
            "representative",
            "representative_role",
            "signing_institution",
            "type",
            "is_primary",
            "version",
            "date_signed",
        )
