from django.urls import path
from .views import *

urlpatterns = [
    path("orders/", KitchenOrdersAPIView.as_view(), name="kitchen_orders"),
    path("orders/<int:order_id>/preparing/", MarkPreparingAPIView.as_view(), name="mark_preparing"),
    path("orders/<int:order_id>/ready/", MarkReadyAPIView.as_view(), name="mark_ready"),
]