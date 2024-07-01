from anvil_consortium_manager.models import AnVILProjectManagerAccess
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType

from . import models


class SignedAgreementViewPermissionMixin(UserPassesTestMixin):
    """Mixin to check if the user has permission to view a SignedAgreement.
    The user has permission to view an agreement if:
        - they have ACM Staff View permission, or
        - they are the signing representative for the agreement, or
        - they are an accessor for the agreement, or
        - they are an uploader for the agreement.
    """

    def get_signed_agreement(self):
        qs = models.SignedAgreement.objects.filter(cc_id=self.kwargs.get("cc_id"))
        if qs.count() == 1:
            return qs.first()

    def test_func(self):
        # The user has ACM Staff View permission
        apm_content_type = ContentType.objects.get_for_model(AnVILProjectManagerAccess)
        required_permission = f"{apm_content_type.app_label}.{AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME}"
        has_acm_permission = self.request.user.has_perm(required_permission)
        # Or is listed on the agreement.
        signed_agreement = self.get_signed_agreement()
        if not signed_agreement:
            is_representative = False
            is_accessor = False
            is_uploader = False
        else:
            is_representative = self.request.user == signed_agreement.representative
            is_accessor = self.request.user in signed_agreement.accessors.all()
            is_uploader = (
                hasattr(signed_agreement, "dataaffiliateagreement")
                and self.request.user in signed_agreement.dataaffiliateagreement.uploaders.all()
            )
        return has_acm_permission or is_representative or is_accessor or is_uploader
