from core.authentication.viewsets.register import RegisterViewSet
from rest_framework import routers
from core.user.viewsets import UserViewSet

router = routers.SimpleRouter()
router.register(r'edit', UserViewSet, basename='users')

router.register(r'register', RegisterViewSet, basename='register')

urlpatterns = [
    *router.urls,
]