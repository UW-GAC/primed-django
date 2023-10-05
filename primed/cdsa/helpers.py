from anvil_consortium_manager.models import GroupAccountMembership

from . import models, tables


def get_representative_records_table():
    """Return the queryset for representative records."""
    qs = models.SignedAgreement.active.all()
    return tables.RepresentativeRecordsTable(qs)


def get_study_records_table():
    """Return the queryset for study records."""
    qs = models.DataAffiliateAgreement.objects.filter(
        signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
        signed_agreement__is_primary=True,
    )
    return tables.StudyRecordsTable(qs)


def get_user_access_records_table():
    """Return the queryset for user access records."""
    qs = GroupAccountMembership.objects.filter(
        group__signedagreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
        group__signedagreement__isnull=False,
    )
    return tables.UserAccessRecordsTable(qs)


def get_cdsa_workspace_records_table():
    """Return the queryset for workspace records."""
    active_data_affiliates = models.DataAffiliateAgreement.objects.filter(
        signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
    )
    qs = models.CDSAWorkspace.objects.filter(
        study__dataaffiliateagreement__in=active_data_affiliates,
    )
    return tables.CDSAWorkspaceRecordsTable(qs)
