from rest_framework import serializers
from .models import Bill
from orders.serializers import OrderSerializer


class BillSerializer(serializers.ModelSerializer):
    order_detail = OrderSerializer(source="order", read_only=True)

    class Meta:
        model = Bill
        fields = [
            "id",
            "order",
            "order_detail",
            "bill_number",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "grand_total",
            "payment_status",
            "created_at",
        ]