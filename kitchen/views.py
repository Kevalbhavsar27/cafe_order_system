from rest_framework.views import APIView
from rest_framework.response import Response

from orders.models import *
from orders.serializers import OrderSerializer
from .permissions import IsAdminOrKitchen


class KitchenOrdersAPIView(APIView):
    permission_classes = [IsAdminOrKitchen]

    def get(self, request):
        orders = Order.objects.select_related("table").prefetch_related("items__menu_item").filter(
            status__in=["ACCEPTED", "PREPARING"]
        )

        serializer = OrderSerializer(orders, many=True)

        return Response(serializer.data)


class MarkPreparingAPIView(APIView):
    permission_classes = [IsAdminOrKitchen]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, status="ACCEPTED")
        except Order.DoesNotExist:
            return Response({"error": "Accepted order not found"}, status=404)

        order.status = "PREPARING"
        order.save(update_fields=["status", "updated_at"])

        return Response({"message": "Order marked as preparing"})


class MarkReadyAPIView(APIView):
    permission_classes = [IsAdminOrKitchen]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, status="PREPARING")
        except Order.DoesNotExist:
            return Response({"error": "Preparing order not found"}, status=404)

        order.status = "READY"
        order.save(update_fields=["status", "updated_at"])

        return Response({"message": "Order marked as ready"})