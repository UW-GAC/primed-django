from anvil_consortium_manager.models import AnVILProjectManagerAccess
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType


class dbGaPApplicationViewPermissionMixin(UserPassesTestMixin):
    """Mixin to check if the user has permission to view a dbGaP application.

    The user has permission to view a dbGaP application if they have ACM Staff View permission or
    if they are the PI of the dbGaP application.
    """

    def get_dbgap_application(self):
        raise NotImplementedError("You must implement get_dbgap_application method in your view.")

    def test_func(self):
        # The user has ACM Staff View permission
        apm_content_type = ContentType.objects.get_for_model(AnVILProjectManagerAccess)
        required_permission = f"{apm_content_type.app_label}.{AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME}"
        has_acm_permission = self.request.user.has_perm(required_permission)
        # Or the user is the PI of the application.
        self.dbgap_application = self.get_dbgap_application()
        if not self.dbgap_application:
            is_pi = False
            is_collaborator = False
        else:
            is_pi = self.dbgap_application.principal_investigator == self.request.user
            is_collaborator = self.request.user in self.dbgap_application.collaborators.all()
        return has_acm_permission or is_pi or is_collaborator
