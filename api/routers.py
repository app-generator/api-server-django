from api.authentication.viewsets.register import RegisterViewSet
from rest_framework import routers
from api.user.viewsets import UserViewSet

router = routers.SimpleRouter(trailing_slash=False)

router.register(r'edit', UserViewSet, basename='users')

router.register(r'register', RegisterViewSet, basename='register')

urlpatterns = [
    *router.urls,
]