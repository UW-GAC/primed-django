from anvil_consortium_manager.forms import FilterForm
from anvil_consortium_manager.models import Account
from django_filters import FilterSet

from .models import Study


class AccountListFilter(FilterSet):
    class Meta:
        model = Account
        fields = {"email": ["icontains"], "user__name": ["icontains"]}
        form = FilterForm


class StudyListFilter(FilterSet):
    class Meta:
        model = Study
        fields = {"short_name": ["icontains"], "full_name": ["icontains"]}
        form = FilterForm
