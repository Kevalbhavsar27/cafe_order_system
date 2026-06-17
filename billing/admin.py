from django.contrib import admin
from .models import Bill


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = [
        "bill_number",
        "order",
        "subtotal",
        "tax_amount",
        "discount_amount",
        "grand_total",
        "payment_status",
        "created_at",
    ]
    list_filter = ["payment_status", "created_at"]
    search_fields = ["bill_number", "order__id"]