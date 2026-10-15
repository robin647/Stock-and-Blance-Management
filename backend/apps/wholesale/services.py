from decimal import Decimal

from django.db.models import DecimalField, F, IntegerField, Max, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, Greatest
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError

from .models import WholesaleInvoice, WholesaleParty, WholesalePayment, WholesaleReturn

ZERO = Decimal("0.00")


def party_account_statement(*, party, start_date=None, end_date=None, transaction_type=None,
                            invoice_number=None, product_id=None, limit=20, offset=0):
    """Return a paginated chronological ledger and date-range balances for one party."""
    sales = WholesaleInvoice.objects.filter(party=party).prefetch_related("items__product")
    payments = WholesalePayment.objects.filter(invoice__party=party).select_related("invoice")
    returns = WholesaleReturn.objects.filter(invoice_item__invoice__party=party).select_related(
        "invoice_item__invoice", "invoice_item__product"
    )

    opening_balance = ZERO
    if start_date:
        opening_balance += _sales_amount(sales.filter(sale_date__lt=start_date))
        opening_balance -= _payment_amount(payments.filter(payment_date__lt=start_date))
        opening_balance -= _return_amount(returns.filter(return_date__lt=start_date))

    period_sales = sales
    period_payments = payments
    period_returns = returns
    if start_date:
        period_sales = period_sales.filter(sale_date__gte=start_date)
        period_payments = period_payments.filter(payment_date__gte=start_date)
        period_returns = period_returns.filter(return_date__gte=start_date)
    if end_date:
        period_sales = period_sales.filter(sale_date__lte=end_date)
        period_payments = period_payments.filter(payment_date__lte=end_date)
        period_returns = period_returns.filter(return_date__lte=end_date)

    balance_sales, balance_payments, balance_returns = period_sales, period_payments, period_returns
    closing_balance = (
        opening_balance + _sales_amount(balance_sales) - _payment_amount(balance_payments)
        - _return_amount(balance_returns)
    )
    if invoice_number:
        period_sales = period_sales.filter(invoice_number__icontains=invoice_number)
        period_payments = period_payments.filter(invoice__invoice_number__icontains=invoice_number)
        period_returns = period_returns.filter(invoice_item__invoice__invoice_number__icontains=invoice_number)
    if product_id:
        period_sales = period_sales.filter(items__product_id=product_id).distinct()
        period_payments = period_payments.filter(invoice__items__product_id=product_id).distinct()
        period_returns = period_returns.filter(invoice_item__product_id=product_id)

    fetch_count = offset + limit + 1
    all_events = _statement_events(period_sales, period_payments, period_returns, fetch_count, product_id)
    selected_type = (transaction_type or "").lower()
    events = [event for event in all_events if not selected_type or event["type"] == selected_type]
    total_count = sum((
        period_sales.count() if not selected_type or selected_type == "sale" else 0,
        period_payments.count() if not selected_type or selected_type == "payment" else 0,
        period_returns.count() if not selected_type or selected_type == "return" else 0,
    ))
    page = events[offset:offset + limit]
    balance_by_event = {}
    running_balance = opening_balance
    for event in all_events:
        running_balance += event["net_amount"]
        balance_by_event[(event["type"], event["id"])] = running_balance
    for event in page:
        event["running_balance"] = balance_by_event.get((event["type"], event["id"]), opening_balance)

    sales_totals = _sales_totals(period_sales)
    gross = sales_totals["gross"]
    paid = _payment_amount(period_payments)
    returned = _return_amount(period_returns)
    quantity = sales_totals["quantity"]
    return {
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "summary": {
            "total_quantity_sold": quantity,
            "gross_sales": gross,
            "return_quantity": period_returns.aggregate(value=Sum("quantity"))["value"] or 0,
            "return_amount": returned,
            "net_sales": gross - returned,
            "bank_payments": _payment_amount(payments=period_payments, field="bank_amount"),
            "bkash_payments": _payment_amount(payments=period_payments, field="bkash_amount"),
            "cash_payments": _payment_amount(payments=period_payments, field="cash_amount"),
            "total_payments": paid,
            "outstanding_due": max(ZERO, closing_balance),
            "credit_balance": max(ZERO, -closing_balance),
        },
        "count": total_count,
        "results": page,
    }


def _statement_events(sales, payments, returns, fetch_count, product_id=None):
    events = []
    for invoice in sales.order_by("sale_date", "created_at", "id")[:fetch_count]:
        items = [item for item in invoice.items.all() if not product_id or item.product_id == int(product_id)]
        gross = sum((item.line_total for item in items), ZERO)
        events.append({
            "date": invoice.sale_date, "created_at": invoice.created_at, "id": invoice.id,
            "type": "sale", "invoice_number": invoice.invoice_number,
            "quantity": sum(item.quantity for item in items), "gross_sale": gross,
            "bank_payment": ZERO, "bkash_payment": ZERO, "cash_payment": ZERO,
            "total_payment": ZERO, "return_quantity": 0, "return_amount": ZERO,
            "net_amount": gross, "reference": "", "notes": invoice.notes,
        })
    for payment in payments.order_by("payment_date", "created_at", "id")[:fetch_count]:
        events.append({
            "date": payment.payment_date, "created_at": payment.created_at, "id": payment.id,
            "type": "payment", "invoice_number": payment.invoice.invoice_number,
            "quantity": 0, "gross_sale": ZERO, "bank_payment": payment.bank_amount,
            "bkash_payment": payment.bkash_amount, "cash_payment": payment.cash_amount,
            "total_payment": payment.total_amount, "return_quantity": 0, "return_amount": ZERO,
            "net_amount": -payment.total_amount, "reference": payment.reference, "notes": payment.notes,
        })
    for entry in returns.order_by("return_date", "created_at", "id")[:fetch_count]:
        events.append({
            "date": entry.return_date, "created_at": entry.created_at, "id": entry.id,
            "type": "return", "invoice_number": entry.invoice_item.invoice.invoice_number,
            "quantity": 0, "gross_sale": ZERO, "bank_payment": ZERO, "bkash_payment": ZERO,
            "cash_payment": ZERO, "total_payment": ZERO, "return_quantity": entry.quantity,
            "return_amount": entry.amount, "net_amount": -entry.amount,
            "reference": "", "notes": entry.notes,
        })
    events.sort(key=lambda row: (row["date"], row["created_at"], row["type"], row["id"]))
    return events


def _sales_amount(queryset):
    return _sales_totals(queryset)["gross"]


def _sales_totals(queryset):
    totals = queryset.aggregate(
        gross=Sum(F("items__quantity") * F("items__unit_price"), output_field=DecimalField(max_digits=18, decimal_places=2)),
        quantity=Sum("items__quantity"),
    )
    return {"gross": totals["gross"] or ZERO, "quantity": totals["quantity"] or 0}


def _payment_amount(payments, field=None):
    if field:
        return payments.aggregate(value=Sum(field))["value"] or ZERO
    rows = payments.aggregate(bank=Sum("bank_amount"), bkash=Sum("bkash_amount"), cash=Sum("cash_amount"))
    return (rows["bank"] or ZERO) + (rows["bkash"] or ZERO) + (rows["cash"] or ZERO)


def _return_amount(queryset):
    return queryset.aggregate(value=Sum("amount"))["value"] or ZERO


def all_party_summary(query_params):
    money_field = DecimalField(max_digits=18, decimal_places=2)
    invoices = WholesaleInvoice.objects.all()
    party_id = query_params.get("party")
    if party_id:
        try:
            party_id = int(party_id)
            if party_id < 1:
                raise ValueError
        except ValueError:
            raise ValidationError({"party": "Party must be a positive integer ID."})
        invoices = invoices.filter(party_id=party_id)
    if query_params.get("invoice_number"):
        invoices = invoices.filter(invoice_number__icontains=query_params["invoice_number"])
    start_date = query_params.get("start_date") or None
    end_date = query_params.get("end_date") or None
    if start_date and not parse_date(start_date):
        raise ValidationError({"start_date": "Use YYYY-MM-DD format."})
    if end_date and not parse_date(end_date):
        raise ValidationError({"end_date": "Use YYYY-MM-DD format."})
    if start_date and end_date and start_date > end_date:
        raise ValidationError({"end_date": "End date must be on or after the start date."})
    if start_date:
        invoices = invoices.filter(sale_date__gte=start_date)
    if end_date:
        invoices = invoices.filter(sale_date__lte=end_date)

    return_totals = WholesaleReturn.objects.filter(
        invoice_item__invoice_id=OuterRef("pk")
    ).order_by().values("invoice_item__invoice_id").annotate(
        amount=Sum("amount"), quantity=Sum("quantity")
    )
    payment_totals = WholesalePayment.objects.filter(invoice_id=OuterRef("pk")).order_by().values(
        "invoice_id"
    ).annotate(
        bank=Sum("bank_amount"), bkash=Sum("bkash_amount"), cash=Sum("cash_amount")
    )
    zero_money = Value(ZERO, output_field=money_field)
    invoices = invoices.annotate(
        gross=Coalesce(
            Sum(F("items__quantity") * F("items__unit_price"), output_field=money_field), zero_money
        ),
        quantity=Coalesce(Sum("items__quantity"), Value(0, output_field=IntegerField())),
        returned=Coalesce(Subquery(return_totals.values("amount")[:1], output_field=money_field), zero_money),
        return_quantity=Coalesce(Subquery(return_totals.values("quantity")[:1], output_field=IntegerField()), Value(0, output_field=IntegerField())),
        bank=Coalesce(Subquery(payment_totals.values("bank")[:1], output_field=money_field), zero_money),
        bkash=Coalesce(Subquery(payment_totals.values("bkash")[:1], output_field=money_field), zero_money),
        cash=Coalesce(Subquery(payment_totals.values("cash")[:1], output_field=money_field), zero_money),
    ).annotate(
        net_sales=F("gross") - F("returned"),
        total_payments=F("bank") + F("bkash") + F("cash"),
    ).annotate(
        due=Greatest(zero_money, F("net_sales") - F("total_payments"), output_field=money_field),
        credit=Greatest(zero_money, F("total_payments") - F("net_sales"), output_field=money_field),
    )
    payment_status = (query_params.get("payment_status") or "").lower()
    if payment_status:
        if payment_status not in {"paid", "partial", "due"}:
            raise ValidationError({"payment_status": "Choose paid, partial, or due."})
        if payment_status == "paid":
            invoices = invoices.filter(due=ZERO)
        elif payment_status == "partial":
            invoices = invoices.filter(due__gt=ZERO, total_payments__gt=ZERO)
        elif payment_status == "due":
            invoices = invoices.filter(due__gt=ZERO, total_payments=ZERO)
        else:
            invoices = invoices.none()

    grouped = invoices.values("party_id", "party__name").annotate(
        total_sales=Sum("net_sales"), total_payments=Sum("total_payments"),
        total_returns=Sum("returned"), total_due=Sum("due"), total_credit=Sum("credit"),
        total_products=Sum("quantity"), last_purchase_date=Max("sale_date"),
    )
    rows_by_party = {row["party_id"]: row for row in grouped}
    search = (query_params.get("search") or "").casefold()
    parties = WholesaleParty.objects.all()
    if party_id:
        parties = parties.filter(pk=party_id)
    if search:
        parties = parties.filter(Q(name__icontains=search) | Q(phone__icontains=search))
    result = []
    for party in parties:
        row = rows_by_party.get(party.pk, {})
        result.append({
            "party_id": party.pk,
            "party_name": party.name,
            "total_sales": row.get("total_sales") or ZERO,
            "total_payments": row.get("total_payments") or ZERO,
            "total_returns": row.get("total_returns") or ZERO,
            "total_due": row.get("total_due") or ZERO,
            "total_credit": row.get("total_credit") or ZERO,
            "total_products": row.get("total_products") or 0,
            "last_purchase_date": row.get("last_purchase_date"),
        })
    ordering = query_params.get("ordering", "party_name")
    sort_key = ordering.lstrip("-")
    allowed_sort_keys = {"party_name", "total_sales", "total_payments", "total_returns", "total_due", "total_products", "last_purchase_date"}
    if sort_key in allowed_sort_keys:
        result.sort(key=lambda row: row[sort_key] or ("" if sort_key in {"party_name", "last_purchase_date"} else 0),
                    reverse=ordering.startswith("-"))
    totals = {key: sum((row[key] for row in result), ZERO) for key in
              ["total_sales", "total_payments", "total_returns", "total_due", "total_credit"]}
    totals["total_products"] = sum(row["total_products"] for row in result)
    return result, totals