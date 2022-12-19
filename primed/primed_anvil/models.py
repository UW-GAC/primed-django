from django.conf import settings
from django.db import models
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel
from simple_history.models import HistoricalRecords


class Study(TimeStampedModel, models.Model):
    """A model to track studies."""

    short_name = models.CharField(
        max_length=31, unique=True, help_text="The short name for this Study."
    )
    full_name = models.CharField(
        max_length=255, help_text="The full name for this Study."
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "studies"

    def __str__(self):
        """String method.
        Returns:
            A string showing the short name of the object.
        """
        return self.short_name

    def get_absolute_url(self):
        """Return the absolute url for this object."""
        return reverse("primed_anvil:studies:detail", args=[self.pk])


class StudySite(TimeStampedModel, models.Model):
    """A model to track Research Centers."""

    short_name = models.CharField(max_length=15, unique=True)
    """The short name of the Research Center."""

    full_name = models.CharField(max_length=255)
    """The full name of the Research Center."""

    def __str__(self):
        """String method.

        Returns:
            A string showing the short name of the object.
        """
        return self.short_name

    def get_absolute_url(self):
        """Return the absolute url for this object."""
        return reverse("primed_anvil:study_sites:detail", args=[self.pk])


class RequesterModel(models.Model):
    """An abstract model for tracking a `requested_by` field."""

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        help_text="The user who requested creation.",
    )

    class Meta:
        abstract = True
