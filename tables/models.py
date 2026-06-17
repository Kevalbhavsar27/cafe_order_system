from django.db import models
from django.core.files.base import ContentFile
from django.conf import settings
import qrcode
from io import BytesIO


class CafeTable(models.Model):
    TABLE_STATUS_CHOICES = (
    ("AVAILABLE", "Available"),
    ("OCCUPIED", "Occupied"),
    ("BILL_PENDING", "Bill Pending"),
    ("CLEANING", "Cleaning"),
    )
    table_number = models.PositiveIntegerField(unique=True)
    table_name = models.CharField(max_length=100, blank=True, null=True)
    capacity = models.PositiveIntegerField(default=2)
    qr_code = models.ImageField(upload_to="table_qr_codes/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    status = models.CharField(max_length=20,choices=TABLE_STATUS_CHOICES,default="AVAILABLE")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["table_number"]

    def __str__(self):
        return f"Table {self.table_number}"

    def generate_qr_code(self):
        menu_url = f"http://127.0.0.1:8000/table/{self.id}/menu/"

        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=4
        )

        qr.add_data(menu_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")

        file_name = f"table_{self.table_number}_qr.png"

        self.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=["qr_code"])