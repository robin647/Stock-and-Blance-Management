from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils.dateparse import parse_date
from rest_framework import permissions, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.inventory.models import StockAdjustment
from core.pagination import StandardPageNumberPagination

from .models import (
    EasyWholesalePayment, EasyWholesaleReturn, EasyWholesaleSale,
    WholesaleInvoice, WholesaleParty, WholesalePayment, WholesaleReturn,
)
from .serializers import (
    EasyWholesalePaymentSerializer, EasyWholesaleReturnSerializer, EasyWholesaleSaleSerializer,
    InvoiceSerializer, PartySerializer, PaymentCreateSerializer, PaymentSerializer,
    ReturnSerializer, StockAdjustmentSerializer,
)
from .services import all_party_summary


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
    search_fields = ["name", "contact_person", "business_name", "phone"]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["is_active"]

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail="Deactivate parties instead of deleting account records.")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        parties = page if page is not None else queryset
        party_ids = [party.pk for party in parties]
        summary_rows, _ = all_party_summary({"party_ids": party_ids})
        totals_by_party = {row["party_id"]: row for row in summary_rows}
        serializer = self.get_serializer(parties, many=True, context={
            **self.get_serializer_context(), "party_totals": totals_by_party,
        })
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        party = self.get_object()
        filters = _validate_statement_filters(request.query_params)
        page_size = StandardPageNumberPagination().get_page_size(request) or 20
        try:
            page_number = int(request.query_params.get("page", "1"))
        except ValueError:
            raise ValidationError({"page": "Page must be a positive integer."})
        if page_number < 1:
            raise ValidationError({"page": "Page must be a positive integer."})
        from .services import party_account_statement

        statement = party_account_statement(
            party=party,
            **filters,
            limit=page_size,
            offset=(page_number - 1) * page_size,
        )
        statement["results"] = [
            {key: value for key, value in event.items() if key != "created_at"}
            for event in statement["results"]
        ]
        next_url = previous_url = None
        if page_number * page_size < statement["count"]:
            params = request.query_params.copy()
            params["page"] = str(page_number + 1)
            next_url = request.build_absolute_uri(f"{request.path}?{params.urlencode()}")
        if page_number > 1:
            params = request.query_params.copy()
            params["page"] = str(page_number - 1)
            previous_url = request.build_absolute_uri(f"{request.path}?{params.urlencode()}")
        return Response({
            "party": PartySerializer(party, context=self.get_serializer_context()).data,
            "summary": statement["summary"],
            "opening_balance": statement["opening_balance"],
            "closing_balance": statement["closing_balance"],
            "count": statement["count"],
            "next": next_url,
            "previous": previous_url,
            "results": statement["results"],
        })

    @action(detail=True, methods=["get"], url_path="statement/export")
    def export_statement(self, request, pk=None):
        from .excel_export import party_statement_excel

        return party_statement_excel(self.get_object(), _validate_statement_filters(request.query_params))


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
        party_id = self.request.query_params.get("party")
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        if party_id:
            queryset = queryset.filter(invoice__party_id=party_id)
        return queryset

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
        party_id = self.request.query_params.get("party")
        if start_date:
            queryset = queryset.filter(return_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(return_date__lte=end_date)
        if invoice_number:
            queryset = queryset.filter(invoice_item__invoice__invoice_number__icontains=invoice_number)
        if party_id:
            queryset = queryset.filter(invoice_item__invoice__party_id=party_id)
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


class EasyTransactionViewSet(AdminOnlyViewSet):
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        party_id = self.request.query_params.get("party")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if party_id:
            queryset = queryset.filter(party_id=party_id)
        if start_date:
            queryset = queryset.filter(**{f"{self.date_field}__gte": start_date})
        if end_date:
            queryset = queryset.filter(**{f"{self.date_field}__lte": end_date})
        return queryset


class EasyWholesaleSaleViewSet(EasyTransactionViewSet):
    queryset = EasyWholesaleSale.objects.select_related("party", "product", "showroom", "created_by")
    serializer_class = EasyWholesaleSaleSerializer
    date_field = "sale_date"


class EasyWholesalePaymentViewSet(EasyTransactionViewSet):
    queryset = EasyWholesalePayment.objects.select_related("party", "created_by")
    serializer_class = EasyWholesalePaymentSerializer
    date_field = "payment_date"


class EasyWholesaleReturnViewSet(EasyTransactionViewSet):
    queryset = EasyWholesaleReturn.objects.select_related("party", "product", "easy_sale", "showroom", "created_by")
    serializer_class = EasyWholesaleReturnSerializer
    date_field = "return_date"


class PartySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can access wholesale summaries.")
        result, totals = all_party_summary(request.query_params)
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


def _validate_statement_filters(params):
    start_date = params.get("start_date") or None
    end_date = params.get("end_date") or None
    if start_date and not parse_date(start_date):
        raise ValidationError({"start_date": "Use YYYY-MM-DD format."})
    if end_date and not parse_date(end_date):
        raise ValidationError({"end_date": "Use YYYY-MM-DD format."})
    if start_date and end_date and start_date > end_date:
        raise ValidationError({"end_date": "End date must be on or after the start date."})
    transaction_type = params.get("transaction_type") or None
    if transaction_type and transaction_type.lower() not in {"sale", "payment", "return"}:
        raise ValidationError({"transaction_type": "Choose sale, payment, or return."})
    product_id = params.get("product") or None
    if product_id:
        try:
            product_id = int(product_id)
            if product_id < 1:
                raise ValueError
        except ValueError:
            raise ValidationError({"product": "Product must be a positive integer ID."})
    return {
        "start_date": start_date,
        "end_date": end_date,
        "transaction_type": transaction_type,
        "invoice_number": params.get("invoice_number") or None,
        "product_id": product_id,
    }