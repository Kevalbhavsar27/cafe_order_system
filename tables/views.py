from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import FileResponse, Http404

from .models import CafeTable
from .serializers import CafeTableSerializer


class CafeTableViewSet(viewsets.ModelViewSet):
    queryset = CafeTable.objects.all()
    serializer_class = CafeTableSerializer
    permission_classes = [permissions.IsAdminUser]

    search_fields = ["table_number", "table_name"]
    ordering_fields = ["table_number", "created_at"]
    ordering = ["table_number"]

    def get_queryset(self):
        return CafeTable.objects.all().order_by("table_number")

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def qr(self, request, pk=None):
        table = self.get_object()

        if not table.qr_code:
            table.generate_qr_code()
            table.save()

        return Response({
            "table_id": table.id,
            "table_number": table.table_number,
            "qr_code_url": request.build_absolute_uri(table.qr_code.url),
            "menu_url": request.build_absolute_uri(f"/table/{table.id}/menu/")
        })

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def download_qr(self, request, pk=None):
        table = self.get_object()

        if not table.qr_code:
            raise Http404("QR code not found")

        return FileResponse(
            table.qr_code.open("rb"),
            as_attachment=True,
            filename=f"table_{table.table_number}_qr.png"
        )