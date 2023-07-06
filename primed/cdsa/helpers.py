from anvil_consortium_manager.models import GroupAccountMembership

from . import models, tables


def get_representative_records_table():
    """Return the queryset for representative records."""
    qs = models.SignedAgreement.objects.all()
    return tables.RepresentativeRecordsTable(qs)


def get_study_records_table():
    """Return the queryset for study records."""
    qs = models.DataAffiliateAgreement.objects.filter(signed_agreement__is_primary=True)
    return tables.StudyRecordsTable(qs)


def get_user_access_records_table():
    """Return the queryset for user access records."""
    qs = GroupAccountMembership.objects.filter(group__signedagreement__isnull=False)
    return tables.UserAccessRecordsTable(qs)


def get_cdsa_workspace_records_table():
    """Return the queryset for workspace records."""
    qs = models.CDSAWorkspace.objects.all()
    return tables.CDSAWorkspaceRecordsTable(qs)
