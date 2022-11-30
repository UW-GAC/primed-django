from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, ManyToManyField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from primed.primed_anvil.models import StudySite


class User(AbstractUser):
    """Default user for gac-django."""

    #: First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    study_sites = ManyToManyField(StudySite)

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})
