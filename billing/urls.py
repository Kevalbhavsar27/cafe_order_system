from django.urls import path
from .views import BillDetailAPIView, GenerateBillAPIView

urlpatterns = [
    path("order/<int:order_id>/", BillDetailAPIView.as_view(), name="bill_detail"),
    path("order/<int:order_id>/generate/", GenerateBillAPIView.as_view(), name="generate_bill"),
]