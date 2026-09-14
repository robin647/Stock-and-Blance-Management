from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied

from core.permissions import IsAdmin

from .models import Showroom
from .serializers import ShowroomSerializer


class ShowroomViewSet(viewsets.ModelViewSet):
    """
    Admin: full CRUD over all showrooms.
    Showroom user: read-only access to their own showroom only (no listing others).
    """

    serializer_class = ShowroomSerializer
    permission_classes = [permissions.IsAuthenticated]
    # The admin showroom-management screen must be able to operate on every
    # showroom, not only the first page of the global API pagination.
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Showroom.objects.all()
        return Showroom.objects.filter(id=user.showroom_id)

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in permissions.SAFE_METHODS and request.user.role != "admin":
            raise PermissionDenied("Only Admin can manage showrooms.")
