from anvil_consortium_manager.adapters.account import BaseAccountAdapter
from django.db.models import Q

from .filters import AccountListFilter
from .tables import AccountTable


class AccountAdapter(BaseAccountAdapter):
    """Custom account adapter for PRIMED."""

    list_table_class = AccountTable
    list_filterset_class = AccountListFilter

    def get_autocomplete_queryset(self, queryset, q):
        """Filter to Accounts where the email or the associated user name matches the query `q`."""
        if q:
            queryset = queryset.filter(Q(email__icontains=q) | Q(user__name__icontains=q))
        return queryset

    def get_autocomplete_label(self, account):
        """Adapter to provide a label for an account in autocomplete views."""
        if account.user:
            name = account.user.name
        else:
            name = "---"
        return "{} ({})".format(name, account.email)
