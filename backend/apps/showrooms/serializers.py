from django.db import transaction
from rest_framework import serializers

from .models import Showroom


class ShowroomSerializer(serializers.ModelSerializer):
    """
    Admin-facing serializer for showroom business profiles.

    Creating a showroom also creates its one login account in the same
    request: `username` / `password` are write-only inputs that are used to
    create (or update) the linked `accounts.User` (role=showroom_user) —
    this is the account the showroom logs in with on the Showroom Login
    portal. They are never stored on the Showroom model itself.
    """

    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, min_length=6)
    login_username = serializers.SerializerMethodField()
    has_login = serializers.SerializerMethodField()

    class Meta:
        model = Showroom
        fields = [
            "id", "name", "address", "phone", "is_active",
            "username", "password", "login_username", "has_login",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_login_username(self, obj):
        user = obj.login_user
        return user.username if user else None

    def get_has_login(self, obj):
        return obj.login_user is not None

    def validate(self, attrs):
        # Creating a showroom without login credentials is allowed (admin
        # can add them later), but if either field is supplied both must be.
        username = attrs.get("username")
        password = attrs.get("password")
        if bool(username) != bool(password):
            raise serializers.ValidationError(
                "Provide both username and password to set up the login, or neither."
            )
        if username:
            from apps.accounts.models import User

            existing = User.objects.filter(username=username)
            if self.instance is not None:
                existing = existing.exclude(showroom=self.instance)
            if existing.exists():
                raise serializers.ValidationError({"username": "This username is already taken."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from apps.accounts.models import User

        username = validated_data.pop("username", None)
        password = validated_data.pop("password", None)

        showroom = Showroom.objects.create(**validated_data)

        if username:
            user = User(username=username, role=User.Role.SHOWROOM_USER, showroom=showroom)
            user.set_password(password)
            user.full_clean(exclude=["password"])
            user.save()

        return showroom

    @transaction.atomic
    def update(self, instance, validated_data):
        from apps.accounts.models import User

        username = validated_data.pop("username", None)
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if username:
            user = instance.login_user
            if user is None:
                user = User(role=User.Role.SHOWROOM_USER, showroom=instance)
            user.username = username
            user.set_password(password)
            user.full_clean(exclude=["password"])
            user.save()

        # Keeping the showroom and its login account's active state in sync
        # means deactivating a showroom immediately blocks that login too.
        login_user = instance.login_user
        if login_user is not None and login_user.is_active != instance.is_active:
            login_user.is_active = instance.is_active
            login_user.save(update_fields=["is_active"])

        return instance
