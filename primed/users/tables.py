import django_tables2 as tables
from django.contrib.auth import get_user_model

User = get_user_model()


class UserTable(tables.Table):
    """A table for `User`s."""

    username = tables.columns.Column(linkify=True)

    class Meta:
        model = User
        fields = ("username", "name", "email", "study_sites")
