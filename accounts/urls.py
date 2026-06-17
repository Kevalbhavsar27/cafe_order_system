from django.urls import path
from .views import *

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="api_register"),
    path("login/", LoginAPIView.as_view(), name="api_login"),
    path("profile/", ProfileAPIView.as_view(), name="api_profile"),

    path("staff/", StaffListAPIView.as_view(), name="staff_list"),
    path("staff/<int:staff_id>/", StaffDetailAPIView.as_view(), name="staff_detail"),
]