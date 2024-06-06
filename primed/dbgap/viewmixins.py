from anvil_consortium_manager.models import AnVILProjectManagerAccess
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType


class dbGaPApplicationViewPermissionMixin(UserPassesTestMixin):
    """Mixin to check if the user has permission to view a dbGaP application.

    The user has permission to view a dbGaP application if they have ACM Staff View permission or
    if they are the PI of the dbGaP application.
    """

    def test_func(self):
        # The user has ACM Staff View permission
        apm_content_type = ContentType.objects.get_for_model(AnVILProjectManagerAccess)
        required_permission = f"{apm_content_type.app_label}.{AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME}"
        has_acm_permission = self.request.user.has_perm(required_permission)
        # Or the user is the PI of the application.
        self.object = self.get_object()
        is_pi = self.object.principal_investigator == self.request.user
        return has_acm_permission or is_pi
