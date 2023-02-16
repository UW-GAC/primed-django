from django.urls import path

from primed.users.views import (
    UserAutocompleteView,
    user_detail_view,
    user_redirect_view,
    user_update_view,
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("autocomplete/", view=UserAutocompleteView.as_view(), name="autocomplete"),
    path("<str:username>/", view=user_detail_view, name="detail"),
]
