from rest_framework.permissions import BasePermission


class IsAdminUserProfile(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff or request.user.is_superuser:
            return True

        profile = getattr(request.user, "profile", None)
        return profile and profile.role == "ADMIN"