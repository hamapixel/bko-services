"""Versioned API routes and technical Django administration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/locations/", include("apps.locations.urls")),
    path("api/v1/catalog/", include("apps.catalog.urls")),
    path("api/v1/providers/", include("apps.providers.urls")),
    path("", include("apps.core.urls")),
]
