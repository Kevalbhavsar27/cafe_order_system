from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Category, MenuItem
from .serializers import CategorySerializer, MenuItemSerializer
from .permissions import IsAdminOrReadOnly
from tables.models import CafeTable


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.select_related("category").all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAdminOrReadOnly]

    filterset_fields = ["category", "is_available"]
    search_fields = ["name", "description", "category__name"]
    ordering_fields = ["name", "price", "created_at"]
    ordering = ["name"]


class PublicTableMenuAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, table_id):
        try:
            table = CafeTable.objects.get(id=table_id, is_active=True)
        except CafeTable.DoesNotExist:
            return Response({"error": "Invalid or inactive table"}, status=404)

        categories = Category.objects.filter(is_active=True).prefetch_related("menu_items")

        category_data = []

        for category in categories:
            items = category.menu_items.filter(is_available=True)
            category_data.append({
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "items": MenuItemSerializer(items,many=True,context={"request": request}).data
            })

        return Response({
            "table": {"id": table.id,"table_number": table.table_number,"table_name": table.table_name,},
            "categories": category_data
        })