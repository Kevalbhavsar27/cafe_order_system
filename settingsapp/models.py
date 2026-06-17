from django.db import models


class CafeSetting(models.Model):
    cafe_name = models.CharField(max_length=150, default="Cafe QR Ordering")
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gst_number = models.CharField(max_length=30, blank=True, null=True)
    invoice_footer = models.CharField(max_length=255, default="Thank you! Visit again.")
    logo = models.ImageField(upload_to="cafe_logo/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cafe_name

    @staticmethod
    def get_settings():
        obj, created = CafeSetting.objects.get_or_create(id=1)
        return obj