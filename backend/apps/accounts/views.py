from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from core.permissions import IsAdmin

from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    ShowroomUserCreateSerializer,
    ShowroomUserUpdateSerializer,
    UserSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    The one and only login endpoint. Both the Admin Login and the Showroom
    Login portal on the frontend post here — the account's `role` (embedded
    in the returned JWT) is what tells the frontend which dashboard and
    permissions to apply, not which endpoint was called.
    """

    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    """Returns the logged-in user's own profile (role, showroom, etc)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ShowroomUserListCreateView(generics.ListCreateAPIView):
    """Admin-only: list all showroom login accounts, or create a new one."""

    permission_classes = [IsAdmin]
    queryset = User.objects.filter(role=User.Role.SHOWROOM_USER).select_related("showroom")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ShowroomUserCreateSerializer
        return UserSerializer


class ShowroomUserDetailView(generics.RetrieveUpdateAPIView):
    """Admin-only: view, activate/deactivate, or reset the password of a showroom account."""

    permission_classes = [IsAdmin]
    queryset = User.objects.filter(role=User.Role.SHOWROOM_USER)

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ShowroomUserUpdateSerializer
        return UserSerializer
