from django.urls import path, include

urlpatterns = [
    path('api/users/', include(('core.routers', 'core'), namespace='core-api')),
]
