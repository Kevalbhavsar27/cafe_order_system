from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

from .models import Order, OrderItem
from tables.models import CafeTable
from menu.models import MenuItem


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source="menu_item.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "menu_item", "menu_item_name", "quantity", "price", "subtotal"]
        read_only_fields = ["price", "subtotal"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    table_number = serializers.IntegerField(source="table.table_number", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "table",
            "table_number",
            "customer_name",
            "customer_mobile",
            "status",
            "payment_status",
            "payment_method",
            "total_amount",
            "note",
            "items",
            "created_at",
            "updated_at",
        ]


class PlaceOrderItemSerializer(serializers.Serializer):
    menu_item = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class PlaceOrderSerializer(serializers.Serializer):
    table = serializers.IntegerField()
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_mobile = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    items = PlaceOrderItemSerializer(many=True)

    def validate_table(self, value):
        try:
            table = CafeTable.objects.get(id=value, is_active=True)
        except CafeTable.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive table")

        return table

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must have at least one item")

        return value

    @transaction.atomic
    def create(self, validated_data):
        table = validated_data["table"]
        items_data = validated_data["items"]

        order = Order.objects.create(
            table=table,
            customer_name=validated_data.get("customer_name", ""),
            customer_mobile=validated_data.get("customer_mobile", ""),
            note=validated_data.get("note", ""),
        )

        total = Decimal("0.00")

        for item_data in items_data:
            try:
                menu_item = MenuItem.objects.get(
                    id=item_data["menu_item"],
                    is_available=True
                )
            except MenuItem.DoesNotExist:
                raise serializers.ValidationError("One or more menu items are unavailable")

            quantity = item_data["quantity"]
            price = menu_item.price
            subtotal = price * quantity

            OrderItem.objects.create(order=order,menu_item=menu_item,quantity=quantity,price=price,subtotal=subtotal)

            total += subtotal

        order.total_amount = total
        order.save(update_fields=["total_amount"])

        return order