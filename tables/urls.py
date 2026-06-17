from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CafeTableViewSet

router = DefaultRouter()
router.register("", CafeTableViewSet, basename="tables")

urlpatterns = [
    path("", include(router.urls)),
]