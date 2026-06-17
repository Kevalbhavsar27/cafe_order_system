from django.contrib import admin
from .models import CafeSetting


@admin.register(CafeSetting)
class CafeSettingAdmin(admin.ModelAdmin):
    list_display = ["cafe_name", "phone", "gst_number", "created_at"]