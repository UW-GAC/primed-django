from anvil_consortium_manager.adapters.account import BaseAccountAdapter
from anvil_consortium_manager.tables import AccountTable


class AccountAdapter(BaseAccountAdapter):
    """Custom account adapter for PRIMED."""

    list_table_class = AccountTable
