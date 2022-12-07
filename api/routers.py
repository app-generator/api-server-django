from api.authentication.viewsets import (
    RegisterViewSet,
    LoginViewSet,
    ActiveSessionViewSet,
    LogoutViewSet,
)
from api.authentication.viewsets.social_login import GithubSocialLogin
from rest_framework import routers
from api.user.viewsets import UserViewSet

router = routers.SimpleRouter(trailing_slash=False)

router.register(r"edit", UserViewSet, basename="user-edit")

router.register(r"register", RegisterViewSet, basename="register")

router.register(r"login", LoginViewSet, basename="login")

router.register(r"checkSession", ActiveSessionViewSet, basename="check-session")

router.register(r"logout", LogoutViewSet, basename="logout")

router.register(r"github-login", GithubSocialLogin, basename="github-login")

urlpatterns = [
    *router.urls,
]
