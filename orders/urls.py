from django.urls import path
from .views import *
urlpatterns = [
    path("place/", PlaceOrderAPIView.as_view(), name="place_order"),
    path("status/<int:order_id>/", OrderStatusAPIView.as_view(), name="order_status"),

    path("counter/", CounterOrdersAPIView.as_view(), name="counter_orders"),
    path("<int:order_id>/accept/", AcceptOrderAPIView.as_view(), name="accept_order"),
    path("<int:order_id>/cancel/", CancelOrderAPIView.as_view(), name="cancel_order"),
    path("<int:order_id>/served/", ServedOrderAPIView.as_view(), name="served_order"),
    path("<int:order_id>/paid/", PaidOrderAPIView.as_view(), name="paid_order"),
]