from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, MenuItemViewSet, PublicTableMenuAPIView

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="categories")
router.register("items", MenuItemViewSet, basename="menu-items")

urlpatterns = [
    path("", include(router.urls)),
    path("public/table/<int:table_id>/", PublicTableMenuAPIView.as_view(), name="public_table_menu"),
]