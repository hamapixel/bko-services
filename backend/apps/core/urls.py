from django.urls import path

from .views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("api/v1/health/", health, name="api-health"),
]
