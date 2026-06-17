from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .models import *
from .serializers import OrderSerializer, PlaceOrderSerializer
from .permissions import IsAdminOrCounter


class PlaceOrderAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PlaceOrderSerializer(data=request.data)

        if serializer.is_valid():
            order = serializer.save()

            return Response({
                "message": "Order placed successfully",
                "order": OrderSerializer(order).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderStatusAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, order_id):
        try:
            order = Order.objects.select_related("table").prefetch_related("items__menu_item").get(id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(order)
        return Response(serializer.data)


class CounterOrdersAPIView(APIView):
    permission_classes = [IsAdminOrCounter]

    def get(self, request):
        orders = Order.objects.select_related("table").prefetch_related("items__menu_item").filter(
            status__in=["PENDING", "ACCEPTED", "READY"]
        )

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class AcceptOrderAPIView(APIView):
    permission_classes = [IsAdminOrCounter]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, status="PENDING")
        except Order.DoesNotExist:
            return Response({"error": "Pending order not found"}, status=404)

        order.status = "ACCEPTED"
        order.save(update_fields=["status", "updated_at"])

        return Response({"message": "Order accepted successfully"})


class CancelOrderAPIView(APIView):
    permission_classes = [IsAdminOrCounter]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if order.status in ["SERVED"]:
            return Response({"error": "Served order cannot be cancelled"}, status=400)

        order.status = "CANCELLED"
        order.save(update_fields=["status", "updated_at"])

        return Response({"message": "Order cancelled successfully"})


class ServedOrderAPIView(APIView):
    permission_classes = [IsAdminOrCounter]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, status="READY")
        except Order.DoesNotExist:
            return Response({"error": "Ready order not found"}, status=404)

        order.status = "SERVED"
        order.save(update_fields=["status", "updated_at"])

        return Response({"message": "Order marked as served"})


class PaidOrderAPIView(APIView):
    permission_classes = [IsAdminOrCounter]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        payment_method = request.data.get("payment_method", "CASH")

        if payment_method not in ["CASH", "UPI", "CARD"]:
            return Response({"error": "Invalid payment method"}, status=400)

        order.payment_status = "PAID"
        order.payment_method = payment_method
        order.save(update_fields=["payment_status", "payment_method", "updated_at"])

        return Response({"message": "Payment marked as paid"})