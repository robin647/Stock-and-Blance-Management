from django.db import models


class Showroom(models.Model):
    """
    A showroom's business profile. Login credentials are NOT stored here —
    they live on the `accounts.User` model (role=showroom_user, showroom=this),
    which is the only identity JWTAuthentication can actually resolve a
    request.user from. See apps.showrooms.serializers.ShowroomSerializer for
    how a showroom + its one login account are created together.
    """

    name = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def login_user(self):
        """The single showroom_user account that logs in for this showroom, if any."""
        return self.users.filter(role="showroom_user").first()
