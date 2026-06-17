from decimal import Decimal
from django.db import models
from tables.models import CafeTable
from menu.models import MenuItem


class Order(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("PREPARING", "Preparing"),
        ("READY", "Ready"),
        ("SERVED", "Served"),
        ("CANCELLED", "Cancelled"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("UNPAID", "Unpaid"),
        ("PAID", "Paid"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("NONE", "None"),
        ("CASH", "Cash"),
        ("UPI", "UPI"),
        ("CARD", "Card"),
    )

    table = models.ForeignKey(CafeTable, on_delete=models.PROTECT, related_name="orders")
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_mobile = models.CharField(max_length=15, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="UNPAID")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="NONE")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - Table {self.table.table_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.menu_item.name} x {self.quantity}"