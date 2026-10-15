from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .services import all_party_summary, party_account_statement
from .models import WholesaleInvoice


class WholesaleExcelExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can export wholesale reports.")
        invoices = WholesaleInvoice.objects.select_related("party").prefetch_related("items__product", "items__returns", "payments")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        party_id = request.query_params.get("party")
        if start_date:
            invoices = invoices.filter(sale_date__gte=start_date)
        if end_date:
            invoices = invoices.filter(sale_date__lte=end_date)
        if party_id:
            invoices = invoices.filter(party_id=party_id)

        workbook = Workbook()
        invoice_sheet = workbook.active
        invoice_sheet.title = "Invoices"
        _header(invoice_sheet, ["Date", "Party", "Invoice", "Total Quantity", "Gross Sale", "Bank", "bKash",
                    "Cash", "Payments", "Returns", "Due", "Credit"])
        item_sheet = workbook.create_sheet("Invoice Items")
        _header(item_sheet, ["Invoice", "Product", "Code", "Size", "Qty", "Unit Price", "Line Total",
                             "Returned Qty", "Return Amount"])
        for invoice in invoices:
            payment_totals = [sum((getattr(payment, field) for payment in invoice.payments.all()), 0)
                              for field in ["bank_amount", "bkash_amount", "cash_amount"]]
            invoice_sheet.append([
                invoice.sale_date, invoice.party.name, invoice.invoice_number, invoice.total_quantity,
                invoice.gross_amount, *payment_totals, invoice.payment_total, invoice.return_total, invoice.due_amount,
                invoice.credit_amount,
            ])
            for item in invoice.items.all():
                item_sheet.append([
                    invoice.invoice_number, item.product.name, item.product.code, item.product.size, item.quantity,
                    item.unit_price, item.line_total,
                    sum(entry.quantity for entry in item.returns.all()),
                    sum((entry.amount for entry in item.returns.all()), 0),
                ])

        products = workbook.create_sheet("Product Quantities")
        _header(products, ["Product", "Code", "Quantity Sold", "Quantity Returned", "Return Amount"])
        product_rows = {}
        for invoice in invoices:
            for item in invoice.items.all():
                row = product_rows.setdefault(item.product_id, [item.product.name, item.product.code, 0, 0, 0])
                row[2] += item.quantity
                row[3] += sum(entry.quantity for entry in item.returns.all())
                row[4] += sum((entry.amount for entry in item.returns.all()), 0)
        for row in product_rows.values():
            products.append(row)

        party_sheet = workbook.create_sheet("Party Summary")
        _header(party_sheet, ["Party", "Gross Sales", "Payments", "Returns", "Outstanding Due", "Credit"])
        party_totals = {}
        for invoice in invoices:
            row = party_totals.setdefault(invoice.party_id, [invoice.party.name, 0, 0, 0, 0, 0])
            row[1] += invoice.gross_amount
            row[2] += invoice.payment_total
            row[3] += invoice.return_total
            row[4] += invoice.due_amount
            row[5] += invoice.credit_amount
        for row in party_totals.values():
            party_sheet.append(row)
        for sheet in [invoice_sheet, item_sheet, products, party_sheet]:
            _apply_formats(sheet, 1)

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="wholesale-report.xlsx"'
        workbook.save(response)
        return response


class WholesaleSummaryExcelExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "admin":
            raise PermissionDenied("Only Admin can export wholesale summaries.")
        rows, totals = all_party_summary(request.query_params)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "All Parties Summary"
        _header(sheet, ["Party", "Net Sales", "Payments", "Returns", "Outstanding Due", "Credit", "Products", "Last Purchase"])
        for row in rows:
            sheet.append([
                row["party_name"], row["total_sales"], row["total_payments"], row["total_returns"],
                row["total_due"], row["total_credit"], row["total_products"], row["last_purchase_date"],
            ])
        sheet.append(["Grand Total", totals["total_sales"], totals["total_payments"], totals["total_returns"],
                      totals["total_due"], totals["total_credit"], totals["total_products"], None])
        _apply_formats(sheet, 1)
        _criteria_sheet(workbook, request.query_params)
        return _workbook_response(workbook, "wholesale-all-parties-summary.xlsx")


def party_statement_excel(party, query_params):
    statement = party_account_statement(
        party=party,
        start_date=query_params.get("start_date") or None,
        end_date=query_params.get("end_date") or None,
        transaction_type=query_params.get("transaction_type") or None,
        invoice_number=query_params.get("invoice_number") or None,
        product_id=query_params.get("product_id") or query_params.get("product") or None,
        limit=50001,
    )
    if statement["count"] > 50000:
        return HttpResponse("Statement exceeds the 50,000-row export limit. Apply narrower filters.", status=400)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Account Statement"
    sheet.append(["Party", party.name])
    sheet.append(["Opening Balance", statement["opening_balance"]])
    sheet.append(["Closing Balance", statement["closing_balance"]])
    sheet.append(["Date range", f"{query_params.get('start_date', 'All')} to {query_params.get('end_date', 'All')}"])
    sheet.append([])
    _header(sheet, ["Transaction Date", "Type", "Cash Memo / Bill", "Product Quantity", "Gross Sale", "Bank Payment",
                    "bKash Payment", "Cash Payment", "Total Payment", "Return Quantity", "Return Amount",
                    "Net Transaction", "Running Balance", "Payment Reference", "Notes"])
    for row in statement["results"]:
        sheet.append([
            row["date"], row["type"], row["invoice_number"], row["quantity"], row["gross_sale"],
            row["bank_payment"], row["bkash_payment"], row["cash_payment"], row["total_payment"],
            row["return_quantity"], row["return_amount"], row["net_amount"], row["running_balance"],
            row.get("reference", ""), row["notes"],
        ])
    _apply_formats(sheet, 6)
    sheet.auto_filter.ref = f"A6:O{sheet.max_row}"
    criteria = dict(query_params)
    if query_params.get("product_id"):
        criteria["product"] = query_params["product_id"]
    _criteria_sheet(workbook, criteria)
    return _workbook_response(workbook, f"party-{party.pk}-account-statement.xlsx")


def _header(sheet, labels):
    sheet.append(labels)
    header_row = sheet.max_row
    for cell in sheet[header_row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="315B52")
    sheet.freeze_panes = f"A{header_row + 1}"
    sheet.auto_filter.ref = f"A{header_row}:{get_column_letter(sheet.max_column)}{sheet.max_row}"


def _criteria_sheet(workbook, query_params):
    sheet = workbook.create_sheet("Filters")
    _header(sheet, ["Filter", "Value"])
    for key in ["party", "start_date", "end_date", "invoice_number", "transaction_type", "payment_status", "product", "search"]:
        if query_params.get(key):
            sheet.append([key.replace("_", " ").title(), query_params[key]])


def _workbook_response(workbook, filename):
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    workbook.save(response)
    return response


def _apply_formats(sheet, header_row):
    for column in range(1, sheet.max_column + 1):
        heading = str(sheet.cell(header_row, column).value or "").casefold()
        if "date" in heading:
            number_format = "yyyy-mm-dd"
        elif any(word in heading for word in ["sale", "payment", "amount", "due", "credit", "price", "net"]):
            number_format = '#,##0.00;[Red]-#,##0.00'
        else:
            continue
        for row in range(header_row + 1, sheet.max_row + 1):
            sheet.cell(row, column).number_format = number_format