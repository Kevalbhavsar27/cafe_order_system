from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response

from orders.models import Order
from .models import Bill
from .serializers import BillSerializer
from .permissions import IsAdminOrCounter


class BillDetailAPIView(APIView):
    permission_classes = [IsAdminOrCounter]

    def get(self, request, order_id):
        try:
            bill = Bill.objects.select_related("order", "order__table").prefetch_related(
                "order__items__menu_item"
            ).get(order_id=order_id)
        except Bill.DoesNotExist:
            return Response({"error": "Bill not found"}, status=404)

        serializer = BillSerializer(bill)

        return Response(serializer.data)


class GenerateBillAPIView(APIView):
    permission_classes = [IsAdminOrCounter]

    def post(self, request, order_id):
        try:
            order = Order.objects.prefetch_related("items").get(id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if order.status == "CANCELLED":
            return Response({"error": "Cancelled order bill cannot be generated"}, status=400)

        if hasattr(order, "bill"):
            serializer = BillSerializer(order.bill)
            return Response({
                "message": "Bill already generated",
                "bill": serializer.data
            })

        subtotal = order.total_amount
        tax_percent = Decimal(str(request.data.get("tax_percent", "0")))
        discount_amount = Decimal(str(request.data.get("discount_amount", "0")))

        tax_amount = (subtotal * tax_percent) / Decimal("100")
        grand_total = subtotal + tax_amount - discount_amount

        if grand_total < 0:
            return Response({"error": "Grand total cannot be negative"}, status=400)

        bill = Bill.objects.create(
            order=order,
            bill_number=Bill.generate_bill_number(),
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            grand_total=grand_total,
            payment_status=order.payment_status,
        )

        serializer = BillSerializer(bill)

        return Response({
            "message": "Bill generated successfully",
            "bill": serializer.data
        }, status=201)