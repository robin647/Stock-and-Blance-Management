from datetime import date

from django.db.models import Q, Sum
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import DailyBalance, StockTransfer
from apps.showrooms.models import Showroom

from .helpers import resolve_showroom_scope


def stock_activity_for_date(showroom_id, target_date, product_id=None, category_id=None):
    """Build a dated stock report from the same transfer ledger that updates inventory."""
    transfers = StockTransfer.objects.filter(showroom_id=showroom_id, date__lte=target_date)
    if product_id:
        transfers = transfers.filter(product_id=product_id)
    if category_id:
        transfers = transfers.filter(product__category_id=category_id)

    activity = (
        transfers
        .values("product__id", "product__name")
        .annotate(
            opening_received=Sum("quantity", filter=Q(transfer_type="receive", date__lt=target_date)),
            opening_sold=Sum("quantity", filter=Q(transfer_type="sale", date__lt=target_date)),
            opening_returned=Sum("quantity", filter=Q(transfer_type="return", date__lt=target_date)),
            received=Sum("quantity", filter=Q(transfer_type="receive", date=target_date)),
            sold=Sum("quantity", filter=Q(transfer_type="sale", date=target_date)),
            returned=Sum("quantity", filter=Q(transfer_type="return", date=target_date)),
        )
        .order_by("product__name")
    )
    rows = []
    for item in activity:
        opening = (item["opening_received"] or 0) - (item["opening_sold"] or 0) - (item["opening_returned"] or 0)
        received = item["received"] or 0
        sold = item["sold"] or 0
        returned = item["returned"] or 0
        rows.append({
            "product_id": item["product__id"],
            "product": item["product__name"],
            "opening": opening,
            "received": received,
            "sold": sold,
            "return": returned,
            "closing": opening + received - sold - returned,
        })
    return rows


class DashboardView(APIView):
    """
    Admin: totals across all showrooms for today + showroom-wise breakdown.
    Showroom user: today's own numbers only.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = request.query_params.get("date", date.today().isoformat())
        showrooms_qs, showroom_id = resolve_showroom_scope(request)

        balances = DailyBalance.objects.filter(date=today, showroom__in=showrooms_qs)
        if showroom_id:
            balances = balances.filter(showroom_id=showroom_id)

        totals = balances.aggregate(
            total_sale=Sum("total_sale"),
            cash_sale=Sum("cash_sale"),
            card_sale=Sum("card_sale"),
            expense=Sum("expense"),
            salary=Sum("salary"),
            deposit=Sum("deposit"),
        )
        totals = {k: (v or 0) for k, v in totals.items()}

        data = {
            "date": today,
            "total_showrooms": showrooms_qs.count(),
            **totals,
            "showroom_wise": list(
                balances.values("showroom__id", "showroom__name").annotate(
                    total_sale=Sum("total_sale"),
                    cash_sale=Sum("cash_sale"),
                    card_sale=Sum("card_sale"),
                )
            ),
        }

        if request.user.role != "admin":
            data.pop("showroom_wise", None)
            data.pop("total_showrooms", None)

        return Response(data)


class DailyStatementView(APIView):
    """Returns the full daily statement (stock table + balance row) for one showroom + date."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        target_date = request.query_params.get("date", date.today().isoformat())
        showrooms_qs, showroom_id = resolve_showroom_scope(request)

        if not showroom_id:
            return Response({"detail": "showroom parameter is required."}, status=400)

        product_id = request.query_params.get("product")
        category_id = request.query_params.get("category")
        stock = stock_activity_for_date(showroom_id, target_date, product_id, category_id)

        balance = DailyBalance.objects.filter(showroom_id=showroom_id, date=target_date).first()

        return Response({
            "date": target_date,
            "showroom": Showroom.objects.filter(id=showroom_id).values("id", "name").first(),
            "stock": stock,
            "balance": {
                "opening_balance": balance.opening_balance,
                "cash_sale": balance.cash_sale,
                "card_sale": balance.card_sale,
                "total_sale": balance.total_sale,
                "expense": balance.expense,
                "salary": balance.salary,
                "deposit": balance.deposit,
                "closing_balance": balance.closing_balance,
            } if balance else None,
        })


class MonthlyReportView(APIView):
    """Aggregated monthly totals for a showroom (or all showrooms for admin)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year = int(request.query_params.get("year", date.today().year))
        month = int(request.query_params.get("month", date.today().month))
        showrooms_qs, showroom_id = resolve_showroom_scope(request)

        balances = DailyBalance.objects.filter(
            date__year=year, date__month=month, showroom__in=showrooms_qs
        )
        if showroom_id:
            balances = balances.filter(showroom_id=showroom_id)

        summary = balances.values("showroom__id", "showroom__name").annotate(
            total_sale=Sum("total_sale"),
            cash_sale=Sum("cash_sale"),
            card_sale=Sum("card_sale"),
            expense=Sum("expense"),
            salary=Sum("salary"),
            deposit=Sum("deposit"),
        )

        stock_qs = StockTransfer.objects.filter(
            date__year=year, date__month=month, showroom__in=showrooms_qs
        )
        if showroom_id:
            stock_qs = stock_qs.filter(showroom_id=showroom_id)
        product_id = request.query_params.get("product")
        category_id = request.query_params.get("category")
        if product_id:
            stock_qs = stock_qs.filter(product_id=product_id)
        if category_id:
            stock_qs = stock_qs.filter(product__category_id=category_id)

        stock_summary = stock_qs.values("product__id", "product__name").annotate(
            received=Sum("quantity", filter=Q(transfer_type="receive")),
            sold=Sum("quantity", filter=Q(transfer_type="sale")),
            returned=Sum("quantity", filter=Q(transfer_type="return")),
        )

        return Response({
            "year": year,
            "month": month,
            "balance_summary": list(summary),
            "stock_summary": list(stock_summary),
        })
