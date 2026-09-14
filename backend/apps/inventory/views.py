from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.response import Response

from .models import DailyBalance, DailyStock, FactoryStock, ShowroomStock, StockTransfer
from .serializers import (
    DailyBalanceSerializer,
    DailyStockSerializer,
    FactoryStockSerializer,
    ShowroomStockSerializer,
    StockTransferSerializer,
)


class ShowroomScopedMixin:
    """
    Shared scoping rule used by both DailyStock and DailyBalance viewsets:
    - Admin sees everything, optionally filtered by ?showroom=<id>.
    - Showroom user only ever sees / writes their OWN showroom's data,
      no matter what showroom_id the client sends in the request body.
      This is the server-side enforcement required by the spec: a
      showroom user cannot access another showroom's data even if the
      frontend is tampered with.
    """

    def get_queryset(self):
        qs = self.queryset_base()
        user = self.request.user
        if user.role == "admin":
            showroom_id = self.request.query_params.get("showroom")
            if showroom_id:
                qs = qs.filter(showroom_id=showroom_id)
        else:
            qs = qs.filter(showroom_id=user.showroom_id)

        product_id = self.request.query_params.get("product")
        date = self.request.query_params.get("date")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if product_id:
            qs = qs.filter(product_id=product_id)
        if date:
            qs = qs.filter(date=date)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "admin":
            if not serializer.validated_data.get("showroom"):
                raise PermissionDenied("Admin must specify a showroom when creating an entry.")
            serializer.save()
        else:
            # Showroom user's own showroom is forced here — any showroom_id
            # sent from the client for this field is silently overridden.
            serializer.save(showroom=user.showroom)


class FactoryStockViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin only: view factory inventory levels"""

    serializer_class = FactoryStockSerializer
    queryset = FactoryStock.objects.select_related("product").all()
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can view factory stock.")


class ShowroomStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin: view all showroom stocks, optionally filtered by ?showroom=<id>
    Showroom user: view only their own stocks
    """

    serializer_class = ShowroomStockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ShowroomStock.objects.select_related("showroom", "product").all()
        user = self.request.user
        if user.role == "admin":
            showroom_id = self.request.query_params.get("showroom")
            if showroom_id:
                qs = qs.filter(showroom_id=showroom_id)
        else:
            qs = qs.filter(showroom_id=user.showroom_id)
        return qs


class StockTransferViewSet(viewsets.ModelViewSet):
    """
    Handle all stock transfers (receive, sale, return):
    - Admin: can view all transfers and create transfers for any showroom
    - Showroom user: can only create transfers for their own showroom
    """

    serializer_class = StockTransferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StockTransfer.objects.select_related("showroom", "product", "created_by").all()
        user = self.request.user
        if user.role == "admin":
            showroom_id = self.request.query_params.get("showroom")
            if showroom_id:
                qs = qs.filter(showroom_id=showroom_id)
        else:
            qs = qs.filter(showroom_id=user.showroom_id)

        # Optional filters
        product_id = self.request.query_params.get("product")
        date = self.request.query_params.get("date")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        transfer_type = self.request.query_params.get("transfer_type")

        if product_id:
            qs = qs.filter(product_id=product_id)
        if date:
            qs = qs.filter(date=date)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if transfer_type:
            qs = qs.filter(transfer_type=transfer_type)

        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "admin":
            if not serializer.validated_data.get("showroom"):
                raise PermissionDenied("Admin must specify a showroom when creating a transfer.")
            serializer.save()
        else:
            # Showroom user can only transfer for their own showroom
            serializer.save(showroom=user.showroom)

    # A transfer is the stock audit trail. Editing or deleting it after the
    # stock rows have changed would make inventory inconsistent.
    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get summary of stock movements (total received, sold, returned)"""
        user = request.user
        showroom_id = request.query_params.get("showroom")

        qs = StockTransfer.objects.all()
        if user.role != "admin":
            qs = qs.filter(showroom_id=user.showroom_id)
        elif showroom_id:
            qs = qs.filter(showroom_id=showroom_id)

        summary = {
            "received": 0,
            "sold": 0,
            "returned": 0,
            "by_product": {},
        }

        for transfer in qs:
            if transfer.transfer_type == "receive":
                summary["received"] += transfer.quantity
            elif transfer.transfer_type == "sale":
                summary["sold"] += transfer.quantity
            elif transfer.transfer_type == "return":
                summary["returned"] += transfer.quantity

            key = f"{transfer.product.id}_{transfer.product.name}"
            if key not in summary["by_product"]:
                summary["by_product"][key] = {"received": 0, "sold": 0, "returned": 0}

            if transfer.transfer_type == "receive":
                summary["by_product"][key]["received"] += transfer.quantity
            elif transfer.transfer_type == "sale":
                summary["by_product"][key]["sold"] += transfer.quantity
            elif transfer.transfer_type == "return":
                summary["by_product"][key]["returned"] += transfer.quantity

        return Response(summary)


class DailyStockViewSet(ShowroomScopedMixin, viewsets.ModelViewSet):
    serializer_class = DailyStockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def queryset_base(self):
        return DailyStock.objects.select_related("showroom", "product").all()


class DailyBalanceViewSet(ShowroomScopedMixin, viewsets.ModelViewSet):
    serializer_class = DailyBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def queryset_base(self):
        return DailyBalance.objects.select_related("showroom").all()
