from django.contrib import admin
from .models import CafeTable


@admin.register(CafeTable)
class CafeTableAdmin(admin.ModelAdmin):
    list_display = ["table_number", "table_name", "capacity", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["table_number", "table_name"]
    readonly_fields = ["qr_code", "created_at"]