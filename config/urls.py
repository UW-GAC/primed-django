from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.templatetags.static import static as static_url_tag
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path("about/", TemplateView.as_view(template_name="pages/about.html"), name="about"),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("primed.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path(
        "anvil/",
        include("anvil_consortium_manager.urls", namespace="anvil_consortium_manager"),
    ),
    path("primed_anvil/", include("primed.primed_anvil.urls", namespace="primed_anvil")),
    path("dbgap/", include("primed.dbgap.urls", namespace="dbgap")),
    path("duo/", include("primed.duo.urls", namespace="duo")),
    path("cdsa/", include("primed.cdsa.urls", namespace="cdsa")),
    path(
        "collaborative_analysis/",
        include("primed.collaborative_analysis.urls", namespace="collaborative_analysis"),
    ),
    path(
        "favicon.ico",
        RedirectView.as_view(url=static_url_tag("images/favicons/primed-favicon.png"), permanent=True),
        name="favicon",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
