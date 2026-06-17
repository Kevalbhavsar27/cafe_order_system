from django.contrib import admin
from .models import *


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["price", "subtotal"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "table", "status", "payment_status", "payment_method", "total_amount", "created_at"]
    list_filter = ["status", "payment_status", "payment_method", "created_at"]
    search_fields = ["id", "table__table_number", "customer_name", "customer_mobile"]
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "menu_item", "quantity", "price", "subtotal"]