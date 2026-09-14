from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Anyone created via `createsuperuser` / create_superuser() is always
        # an Admin — role can't accidentally default to showroom_user here.
        extra_fields.setdefault("role", "admin")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        SHOWROOM_USER = "showroom_user", "Showroom User"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SHOWROOM_USER)

    objects = CustomUserManager()

    # A showroom_user is tied to exactly one showroom. Admin leaves this null.
    # Using a string reference avoids a circular import with the showrooms app.
    showroom = models.ForeignKey(
        "showrooms.Showroom",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )

    def __str__(self):
        return f"{self.username} ({self.role})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.role == self.Role.SHOWROOM_USER and not self.showroom_id:
            raise ValidationError("A showroom user must be assigned to a showroom.")
        if self.role == self.Role.ADMIN and self.showroom_id:
            raise ValidationError("An admin user must not be assigned to a showroom.")
