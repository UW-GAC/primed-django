from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, RedirectView, UpdateView

from primed.cdsa.models import SignedAgreement
from primed.dbgap.models import dbGaPApplication

from .forms import UserLookupForm

User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dbgap_applications"] = dbGaPApplication.objects.filter(
            Q(principal_investigator=self.object) | Q(collaborators=self.object)
        ).distinct()
        context["signed_agreements"] = SignedAgreement.objects.filter(
            Q(representative=self.object) | Q(accessors=self.object) | Q(dataaffiliateagreement__uploaders=self.object)
        ).distinct()
        return context


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        return self.request.user.get_absolute_url()  # type: ignore [union-attr]

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


class UserAutocompleteView(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    """View to provide autocompletion for users. Matches either email or name."""

    def get_result_label(self, result):
        return "{} ({})".format(result.name, result.email)

    def get_queryset(self):
        """Filter to users matching the query."""
        qs = User.objects.all().order_by("username")

        if self.q:
            # Filter to users whose name or email matches the query.
            qs = qs.filter(Q(email__icontains=self.q) | Q(name__icontains=self.q))

        return qs


class UserLookup(LoginRequiredMixin, FormView):
    """view to allow searching by user and redirect to the profile page of the selected user."""

    template_name = "users/userlookup_form.html"
    form_class = UserLookupForm

    def form_valid(self, form):
        self.user = form.cleaned_data["user"]
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to the user profile page after processing a valid form."""

        return reverse("users:detail", kwargs={"username": self.user.username})
