from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "role", "phone"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        role = validated_data.pop("role")
        phone = validated_data.pop("phone", "")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            is_staff=True
        )

        UserProfile.objects.create(user=user, role=role, phone=phone)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data.get("username"), password=data.get("password"))

        if not user:
            raise serializers.ValidationError("Invalid username or password")

        data["user"] = user
        return data


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email")

    class Meta:
        model = UserProfile
        fields = ["id", "username", "email", "role", "phone", "created_at"]


class StaffSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email")
    is_active = serializers.BooleanField(source="user.is_active")

    class Meta:
        model = UserProfile
        fields = ["id", "username", "email", "role", "phone", "is_active", "created_at"]