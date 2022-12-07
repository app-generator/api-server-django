from django.urls import path, include
from django.contrib import admin
from api.authentication.viewsets.social_login import GithubSocialLogin

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/users/", include(("api.routers", "api"), namespace="api")),
    path("api/sessions/oauth/github/", GithubSocialLogin.as_view(), name="github_login"),
]
