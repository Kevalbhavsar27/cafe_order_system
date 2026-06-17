from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer, StaffSerializer
from .models import UserProfile


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            return Response({
                "message": "Staff registered successfully",
                "user": user.username
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={"role": "ADMIN" if user.is_superuser else "COUNTER"}
            )

            tokens = get_tokens_for_user(user)

            return Response({
                "message": "Login successful",
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "role": profile.role,
                }
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"role": "ADMIN" if request.user.is_superuser else "COUNTER"}
        )

        serializer = ProfileSerializer(profile)
        return Response(serializer.data)


class StaffListAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        staff = UserProfile.objects.select_related("user").all().order_by("-created_at")
        serializer = StaffSerializer(staff, many=True)
        return Response(serializer.data)


class StaffDetailAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, staff_id):
        try:
            profile = UserProfile.objects.get(id=staff_id)
        except UserProfile.DoesNotExist:
            return Response({"error": "Staff not found"}, status=404)

        role = request.data.get("role")
        phone = request.data.get("phone")
        is_active = request.data.get("is_active")

        if role:
            if role not in ["ADMIN", "COUNTER", "KITCHEN"]:
                return Response({"error": "Invalid role"}, status=400)
            profile.role = role

        if phone is not None:
            profile.phone = phone

        if is_active is not None:
            profile.user.is_active = is_active
            profile.user.save(update_fields=["is_active"])

        profile.save()
        return Response({"message": "Staff updated successfully"})

    def delete(self, request, staff_id):
        try:
            profile = UserProfile.objects.get(id=staff_id)
        except UserProfile.DoesNotExist:
            return Response({"error": "Staff not found"}, status=404)

        if profile.user == request.user:
            return Response({"error": "You cannot delete your own account"}, status=400)

        profile.user.delete()
        return Response({"message": "Staff deleted successfully"})