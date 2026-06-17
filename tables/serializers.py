from rest_framework import serializers
from .models import CafeTable


class CafeTableSerializer(serializers.ModelSerializer):
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = CafeTable
        fields = [
            "id",
            "table_number",
            "table_name",
            "capacity",
            "qr_code",
            "qr_code_url",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["qr_code", "qr_code_url", "created_at"]

    def get_qr_code_url(self, obj):
        request = self.context.get("request")

        if obj.qr_code and request:
            return request.build_absolute_uri(obj.qr_code.url)

        return None