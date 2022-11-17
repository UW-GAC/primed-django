from django.db import models


class dbGaPDataAccessRequestManager(models.Manager):
    """A custom manager for the dbGaPDataAccessRequest model."""

    def approved(self):
        """Filter to the approved data access requests only."""
        return self.filter(dbgap_current_status=self.model.APPROVED)
