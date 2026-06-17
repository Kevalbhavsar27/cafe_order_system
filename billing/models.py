from decimal import Decimal
from django.db import models
from orders.models import Order


class Bill(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="bill")
    bill_number = models.CharField(max_length=30, unique=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payment_status = models.CharField(max_length=20, default="UNPAID")
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.TextField(blank=True, null=True)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.bill_number

    @staticmethod
    def generate_bill_number():
        last_bill = Bill.objects.order_by("-id").first()

        if last_bill:
            next_id = last_bill.id + 1
        else:
            next_id = 1

        return f"BILL-{next_id:05d}"