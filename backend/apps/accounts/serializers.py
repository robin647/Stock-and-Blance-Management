from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Single login serializer for BOTH Admin and Showroom accounts.

    Every account — Admin or Showroom — is a row on the `User` model,
    authenticated the normal Django way (username + password), which is
    what lets JWTAuthentication resolve `request.user` on every subsequent
    request. Role and showroom info are embedded directly in the JWT
    payload so the frontend knows immediately, without an extra API call,
    whether the logged-in account is an Admin or which Showroom it belongs
    to — and can route it to the right dashboard and permissions.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["showroom_id"] = user.showroom_id
        token["showroom_name"] = user.showroom.name if user.showroom_id else None
        token["full_name"] = user.get_full_name() or user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_active:
            raise serializers.ValidationError(
                {"detail": "This account has been deactivated. Contact the Admin."}
            )
        return data


class UserSerializer(serializers.ModelSerializer):
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email",
            "role", "showroom", "showroom_name", "is_active",
        ]
        read_only_fields = ["id", "role", "showroom"]


class ShowroomUserCreateSerializer(serializers.ModelSerializer):
    """Used by Admin to create a new showroom login account."""

    password = serializers.CharField(write_only=True, min_length=6)
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email",
            "password", "showroom", "showroom_name", "is_active",
        ]

    def validate_showroom(self, showroom):
        if showroom.login_user is not None:
            raise serializers.ValidationError(
                "This showroom already has a login account. Edit or reset that one instead."
            )
        return showroom

    def validate(self, attrs):
        if not attrs.get("showroom"):
            raise serializers.ValidationError({"showroom": "Showroom is required for a showroom user."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(role=User.Role.SHOWROOM_USER, **validated_data)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save()
        return user


class ShowroomUserUpdateSerializer(serializers.ModelSerializer):
    """
    Used by Admin to edit an existing showroom account: activate/deactivate,
    update contact info, or reset the password. `password` is optional here —
    omit it to leave the current password unchanged.
    """

    password = serializers.CharField(write_only=True, required=False, min_length=6)
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email",
            "password", "showroom", "showroom_name", "is_active",
        ]
        read_only_fields = ["id", "showroom", "showroom_name"]

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.full_clean(exclude=["password"])
        instance.save()
        return instance
