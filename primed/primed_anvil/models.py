from django.db import models


class StudySite(models.Model):
    """A model to track Study Sites."""

    short_name = models.CharField(max_length=31, unique=True)
    """The short name for this Study."""

    full_name = models.CharField(max_length=255)
    """The full name for this Study."""

    def __str__(self):
        """String method.
        Returns:
            A string showing the short name of the object.
        """
        return self.short_name


class Study(models.Model):
    """A model to track studies."""

    short_name = models.CharField(max_length=31, unique=True)
    """The short name for this Study."""

    full_name = models.CharField(max_length=255)
    """The full name for this Study."""

    def __str__(self):
        """String method.
        Returns:
            A string showing the short name of the object.
        """
        return self.short_name
