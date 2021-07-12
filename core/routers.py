from rest_framework import routers
from core.user.viewsets import UserViewSet

router = routers.SimpleRouter()

router.register(r'user', UserViewSet, basename='core-user')

urlpatterns = [
    *router.urls
]