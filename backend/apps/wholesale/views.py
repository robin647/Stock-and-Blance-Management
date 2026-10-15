from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import permissions, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.inventory.models import StockAdjustment
from core.pagination import StandardPageNumberPagination

from .models import WholesaleInvoice, WholesaleParty, WholesalePayment, WholesaleReturn
from .serializers import (
    InvoiceSerializer, PartySerializer, PaymentCreateSerializer, PaymentSerializer,
    ReturnSerializer, StockAdjustmentSerializer,
)


class AdminOnlyViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can access wholesale management.")


class PartyViewSet(AdminOnlyViewSet):
    serializer_class = PartySerializer
    queryset = WholesaleParty.objects.prefetch_related(
        "invoices__items", "invoices__items__returns", "invoices__payments"
    )
    search_fields = ["name", "business_name", "phone"]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["is_active"]

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        party = self.get_object()
        invoices = party.invoices.prefetch_related("items__product", "items__returns", "payments")
        return Response({
            "party": PartySerializer(party, context=self.get_serializer_context()).data,
            "invoices": InvoiceSerializer(invoices, many=True).data,
        })


class InvoiceViewSet(AdminOnlyViewSet):
    serializer_class = InvoiceSerializer
    queryset = WholesaleInvoice.objects.select_related("party", "showroom").prefetch_related(
        "items__product", "items__returns", "payments"
    )
    filterset_fields = ["party", "invoice_number", "stock_location"]
    ordering_fields = ["sale_date", "invoice_number", "created_at"]
    ordering = ["-sale_date", "-id"]

    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        payment_status = self.request.query_params.get("payment_status")
        if start_date:
            queryset = queryset.filter(sale_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(sale_date__lte=end_date)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        payment_status = self.request.query_params.get("payment_status")
        if payment_status:
            queryset = [invoice for invoice in queryset if _payment_status(invoice) == payment_status.lower()]
        return queryset

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Invoices cannot be edited; record payments or returns instead.")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Invoices cannot be edited; record payments or returns instead.")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Invoices are immutable and cannot be deleted.")


class PaymentViewSet(AdminOnlyViewSet):
    queryset = WholesalePayment.objects.select_related("invoice", "invoice__party", "created_by")
    serializer_class = PaymentCreateSerializer

    def get_serializer_class(self):
        return PaymentCreateSerializer if self.action == "create" else PaymentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        invoice_id = self.request.query_params.get("invoice")
        return queryset.filter(invoice_id=invoice_id) if invoice_id else queryset

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Payments are immutable; record a new payment entry.")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Payments are immutable; record a new payment entry.")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Payments are immutable.")


class ReturnViewSet(AdminOnlyViewSet):
    queryset = WholesaleReturn.objects.select_related("invoice_item__invoice", "invoice_item__product", "created_by")
    serializer_class = ReturnSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        invoice_number = self.request.query_params.get("invoice_number")
        if start_date:
            queryset = queryset.filter(return_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(return_date__lte=end_date)
        if invoice_number:
            queryset = queryset.filter(invoice_item__invoice__invoice_number__icontains=invoice_number)
        return queryset

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Returns are immutable.")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Returns are immutable.")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Returns are immutable.")


class StockAdjustmentViewSet(AdminOnlyViewSet):
    queryset = StockAdjustment.objects.select_related("product", "showroom", "created_by")
    serializer_class = StockAdjustmentSerializer

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Stock adjustment history is immutable.")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Stock adjustment history is immutable.")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Stock adjustment history is immutable.")


class PartySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can access wholesale summaries.")
        invoices = WholesaleInvoice.objects.select_related("party").prefetch_related("items__returns", "payments")
        party_id = request.query_params.get("party")
        invoice_number = request.query_params.get("invoice_number")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if party_id:
            invoices = invoices.filter(party_id=party_id)
        if invoice_number:
            invoices = invoices.filter(invoice_number__icontains=invoice_number)
        if start_date:
            invoices = invoices.filter(sale_date__gte=start_date)
        if end_date:
            invoices = invoices.filter(sale_date__lte=end_date)

        invoices = list(invoices)
        if request.query_params.get("payment_status"):
            desired_status = request.query_params["payment_status"]
            invoices = [invoice for invoice in invoices if _payment_status(invoice) == desired_status]
        rows = defaultdict(lambda: {"party_id": 0, "party_name": "", "total_sales": Decimal("0"),
                                    "total_payments": Decimal("0"), "total_returns": Decimal("0"),
                                    "total_due": Decimal("0"), "total_credit": Decimal("0"),
                                    "total_products": 0, "last_purchase_date": None})
        for party in WholesaleParty.objects.all():
            if not party_id or str(party.pk) == party_id:
                row = rows[party.pk]
                row["party_id"] = party.pk
                row["party_name"] = party.name
        for invoice in invoices:
            row = rows[invoice.party_id]
            row["party_id"] = invoice.party_id
            row["party_name"] = invoice.party.name
            row["total_sales"] += invoice.gross_amount
            row["total_payments"] += invoice.payment_total
            row["total_returns"] += invoice.return_total
            row["total_due"] += invoice.due_amount
            row["total_credit"] += invoice.credit_amount
            row["total_products"] += invoice.total_quantity
            if row["last_purchase_date"] is None or invoice.sale_date > row["last_purchase_date"]:
                row["last_purchase_date"] = invoice.sale_date
        search = request.query_params.get("search", "").casefold()
        result = [row for row in rows.values() if search in row["party_name"].casefold()]
        ordering = request.query_params.get("ordering", "party_name")
        sort_key = ordering.lstrip("-")
        if sort_key in {"party_name", "total_sales", "total_payments", "total_returns", "total_due", "total_products", "last_purchase_date"}:
            result.sort(key=lambda row: row[sort_key] or ("" if sort_key in {"party_name", "last_purchase_date"} else 0), reverse=ordering.startswith("-"))
        totals = {key: sum((row[key] for row in result), Decimal("0")) for key in
                  ["total_sales", "total_payments", "total_returns", "total_due", "total_credit"]}
        totals["total_products"] = sum(row["total_products"] for row in result)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(result, request, view=self)
        response = paginator.get_paginated_response(page)
        response.data["grand_totals"] = totals
        return response


class WholesaleReportView(PartySummaryView):
    def get(self, request):
        response = super().get(request)
        if response.status_code != 200:
            return response
        invoices = WholesaleInvoice.objects.select_related("party").prefetch_related("items__product", "items__returns", "payments")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            invoices = invoices.filter(sale_date__gte=start_date)
        if end_date:
            invoices = invoices.filter(sale_date__lte=end_date)
        rows = list(invoices)
        product_totals = defaultdict(int)
        payments = defaultdict(lambda: Decimal("0"))
        for invoice in rows:
            for item in invoice.items.all():
                product_totals[item.product.name] += item.quantity
            for payment in invoice.payments.all():
                payments["bank"] += payment.bank_amount
                payments["bkash"] += payment.bkash_amount
                payments["cash"] += payment.cash_amount
        response.data["invoices"] = InvoiceSerializer(rows, many=True).data
        response.data["product_quantities"] = [{"product": name, "quantity": quantity} for name, quantity in sorted(product_totals.items())]
        response.data["payment_breakdown"] = payments
        party_totals = defaultdict(lambda: {"party": "", "sales": Decimal("0"), "payments": Decimal("0"),
                            "returns": Decimal("0"), "due": Decimal("0"), "credit": Decimal("0")})
        for invoice in rows:
            totals = party_totals[invoice.party_id]
            totals["party"] = invoice.party.name
            totals["sales"] += invoice.gross_amount
            totals["payments"] += invoice.payment_total
            totals["returns"] += invoice.return_total
            totals["due"] += invoice.due_amount
            totals["credit"] += invoice.credit_amount
        response.data["party_totals"] = sorted(party_totals.values(), key=lambda row: row["party"])
        return response


def _payment_status(invoice):
    if invoice.due_amount <= 0:
        return "paid"
    if invoice.payment_total > 0:
        return "partial"
    return "due"