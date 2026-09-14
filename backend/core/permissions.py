from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allows access only to Admin role users."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsShowroomUser(BasePermission):
    """Allows access only to Showroom User role users."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "showroom_user"
        )


class IsAdminOrOwnShowroom(BasePermission):
    """
    Admin can access everything.
    Showroom user can only access objects belonging to their own showroom.
    This is enforced again at the queryset level in each view — this
    permission class is a second line of defence for object-level checks.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        showroom_id = getattr(obj, "showroom_id", None)
        return showroom_id == request.user.showroom_id
