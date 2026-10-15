from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import FactoryStock, ShowroomStock, StockAdjustment
from apps.products.models import Product, ProductCategory
from apps.showrooms.models import Showroom


class WholesaleApiTests(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(name="Panjabi")
        self.product = Product.objects.create(
            name="Classic Panjabi", code="3333", category=category, size="42", selling_price=Decimal("120.00")
        )
        self.factory_stock = FactoryStock.objects.create(product=self.product, quantity=20)
        self.showroom = Showroom.objects.create(name="Zone 1")
        self.showroom_stock = ShowroomStock.objects.create(showroom=self.showroom, product=self.product, quantity=8)
        self.admin = User.objects.create_user(username="wholesale-admin", password="password", role="admin")
        self.showroom_user = User.objects.create_user(
            username="wholesale-showroom", password="password", role="showroom_user", showroom=self.showroom
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        party_response = self.client.post("/api/wholesale/parties/", {"name": "Test Buyer"}, format="json")
        self.party_id = party_response.data["id"]

    def test_stock_adjustment_updates_only_selected_location_and_keeps_history(self):
        response = self.client.post("/api/wholesale/stock-adjustments/", {
            "product": self.product.id, "location": "factory", "new_quantity": 25, "reason": "Count correction",
        }, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.factory_stock.refresh_from_db()
        self.showroom_stock.refresh_from_db()
        adjustment = StockAdjustment.objects.get()
        self.assertEqual(self.factory_stock.quantity, 25)
        self.assertEqual(self.showroom_stock.quantity, 8)
        self.assertEqual(adjustment.previous_quantity, 20)
        self.assertEqual(adjustment.difference, 5)
        self.assertEqual(adjustment.reason, "Count correction")
        self.assertEqual(adjustment.created_by, self.admin)

        showroom_response = self.client.post("/api/wholesale/stock-adjustments/", {
            "product": self.product.id, "location": "showroom", "showroom": self.showroom.id,
            "new_quantity": 10, "reason": "Showroom count correction",
        }, format="json")
        self.assertEqual(showroom_response.status_code, 201, showroom_response.data)
        self.factory_stock.refresh_from_db()
        self.showroom_stock.refresh_from_db()
        self.assertEqual(self.factory_stock.quantity, 25)
        self.assertEqual(self.showroom_stock.quantity, 10)

    def test_invoice_payment_and_return_keep_quantities_and_due_consistent(self):
        invoice_response = self.client.post("/api/wholesale/invoices/", {
            "party": self.party_id,
            "invoice_number": "WS-001",
            "sale_date": "2026-10-15",
            "stock_location": "factory",
            "items": [{"product": self.product.id, "quantity": 3, "unit_price": "100.00"}],
            "initial_cash_payment": "50.00",
        }, format="json")

        self.assertEqual(invoice_response.status_code, 201, invoice_response.data)
        invoice_id = invoice_response.data["id"]
        invoice_item_id = invoice_response.data["items"][0]["id"]
        self.assertEqual(invoice_response.data["gross_amount"], "300.00")
        self.assertEqual(invoice_response.data["total_quantity"], 3)
        self.assertEqual(invoice_response.data["due_amount"], "250.00")
        self.factory_stock.refresh_from_db()
        self.assertEqual(self.factory_stock.quantity, 17)

        payment_response = self.client.post("/api/wholesale/payments/", {
            "invoice": invoice_id, "payment_date": "2026-10-15", "bank_amount": "100.00",
            "bkash_amount": "0.00", "cash_amount": "0.00",
        }, format="json")
        self.assertEqual(payment_response.status_code, 201, payment_response.data)

        return_response = self.client.post("/api/wholesale/returns/", {
            "invoice_item": invoice_item_id, "quantity": 1, "amount": "100.00", "return_date": "2026-10-15",
        }, format="json")
        self.assertEqual(return_response.status_code, 201, return_response.data)
        self.factory_stock.refresh_from_db()
        self.assertEqual(self.factory_stock.quantity, 18)

        detail = self.client.get(f"/api/wholesale/invoices/{invoice_id}/")
        self.assertEqual(detail.data["total_payments"], "150.00")
        self.assertEqual(detail.data["return_quantity"], 1)
        self.assertEqual(detail.data["return_amount"], "100.00")
        self.assertEqual(detail.data["due_amount"], "50.00")

    def test_duplicate_invoice_and_excess_return_are_rejected(self):
        payload = {
            "party": self.party_id, "invoice_number": "WS-DUP", "sale_date": "2026-10-15",
            "items": [{"product": self.product.id, "quantity": 2, "unit_price": "100.00"}],
        }
        first = self.client.post("/api/wholesale/invoices/", payload, format="json")
        second = self.client.post("/api/wholesale/invoices/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 400)
        item_id = first.data["items"][0]["id"]
        response = self.client.post("/api/wholesale/returns/", {
            "invoice_item": item_id, "quantity": 3, "amount": "100.00", "return_date": "2026-10-15",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_showroom_invoice_deducts_and_return_restores_only_that_showroom(self):
        invoice = self.client.post("/api/wholesale/invoices/", {
            "party": self.party_id, "invoice_number": "WS-SHOWROOM", "sale_date": "2026-10-15",
            "stock_location": "showroom", "showroom": self.showroom.id,
            "items": [{"product": self.product.id, "quantity": 2, "unit_price": "100.00"}],
        }, format="json")
        self.assertEqual(invoice.status_code, 201, invoice.data)
        self.factory_stock.refresh_from_db()
        self.showroom_stock.refresh_from_db()
        self.assertEqual(self.factory_stock.quantity, 20)
        self.assertEqual(self.showroom_stock.quantity, 6)

        returned = self.client.post("/api/wholesale/returns/", {
            "invoice_item": invoice.data["items"][0]["id"], "quantity": 1,
            "amount": "100.00", "return_date": "2026-10-15",
        }, format="json")
        self.assertEqual(returned.status_code, 201, returned.data)
        self.factory_stock.refresh_from_db()
        self.showroom_stock.refresh_from_db()
        self.assertEqual(self.factory_stock.quantity, 20)
        self.assertEqual(self.showroom_stock.quantity, 7)

    def test_return_after_full_payment_is_tracked_as_credit_not_negative_due(self):
        invoice = self.client.post("/api/wholesale/invoices/", {
            "party": self.party_id, "invoice_number": "WS-CREDIT", "sale_date": "2026-10-15",
            "items": [{"product": self.product.id, "quantity": 2, "unit_price": "100.00"}],
            "initial_cash_payment": "200.00",
        }, format="json")
        self.assertEqual(invoice.status_code, 201, invoice.data)
        returned = self.client.post("/api/wholesale/returns/", {
            "invoice_item": invoice.data["items"][0]["id"], "quantity": 1,
            "amount": "100.00", "return_date": "2026-10-15",
        }, format="json")
        self.assertEqual(returned.status_code, 201, returned.data)
        detail = self.client.get(f"/api/wholesale/invoices/{invoice.data['id']}/")
        self.assertEqual(detail.data["due_amount"], "0.00")
        self.assertEqual(detail.data["credit_amount"], "100.00")

    def test_non_admin_cannot_manage_wholesale_or_stock_adjustments(self):
        self.client.force_authenticate(self.showroom_user)
        party = self.client.post("/api/wholesale/parties/", {"name": "Blocked Buyer"}, format="json")
        adjustment = self.client.post("/api/wholesale/stock-adjustments/", {
            "product": self.product.id, "location": "showroom", "showroom": self.showroom.id,
            "new_quantity": 12, "reason": "Unauthorized",
        }, format="json")
        summary = self.client.get("/api/wholesale/summary/")
        self.assertEqual(party.status_code, 403)
        self.assertEqual(adjustment.status_code, 403)
        self.assertEqual(summary.status_code, 403)

    def test_party_partial_search_edit_and_deactivation(self):
        search = self.client.get("/api/wholesale/parties/", {"search": "test buy"})
        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.data["count"], 1)
        response = self.client.patch(f"/api/wholesale/parties/{self.party_id}/", {
            "contact_person": "A. Buyer", "is_active": False,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["contact_person"], "A. Buyer")
        self.assertFalse(response.data["is_active"])

    def test_statement_uses_actual_payment_date_and_prior_opening_balance(self):
        invoice = self.client.post("/api/wholesale/invoices/", {
            "party": self.party_id, "invoice_number": "WS-DATE-01", "sale_date": "2026-10-01",
            "items": [{"product": self.product.id, "quantity": 2, "unit_price": "100.00"}],
        }, format="json")
        self.assertEqual(invoice.status_code, 201, invoice.data)
        payment = self.client.post("/api/wholesale/payments/", {
            "invoice": invoice.data["id"], "payment_date": "2026-10-12", "bank_amount": "50.00",
            "bkash_amount": "25.00", "cash_amount": "25.00", "reference": "BANK-REF-7",
        }, format="json")
        self.assertEqual(payment.status_code, 201, payment.data)

        statement = self.client.get(f"/api/wholesale/parties/{self.party_id}/history/", {
            "start_date": "2026-10-10", "end_date": "2026-10-15",
        })
        self.assertEqual(statement.status_code, 200, statement.data)
        self.assertEqual(statement.data["opening_balance"], "200.00")
        self.assertEqual(statement.data["summary"]["gross_sales"], "0.00")
        self.assertEqual(statement.data["summary"]["total_payments"], "100.00")
        self.assertEqual(statement.data["summary"]["bank_payments"], "50.00")
        self.assertEqual(statement.data["closing_balance"], "100.00")
        row = statement.data["results"][0]
        self.assertEqual(row["type"], "payment")
        self.assertEqual(row["date"], "2026-10-12")
        self.assertEqual(row["reference"], "BANK-REF-7")
        self.assertEqual(row["running_balance"], "100.00")

        statement_export = self.client.get(
            f"/api/wholesale/parties/{self.party_id}/statement/export/",
            {"start_date": "2026-10-10", "end_date": "2026-10-15"},
        )
        self.assertEqual(statement_export.status_code, 200)
        statement_sheet = load_workbook(BytesIO(statement_export.content), read_only=True)["Account Statement"]
        self.assertIn("BANK-REF-7", [cell for row in statement_sheet.iter_rows(values_only=True) for cell in row])

    def test_all_parties_export_uses_net_sales_and_preserves_summary(self):
        invoice = self.client.post("/api/wholesale/invoices/", {
            "party": self.party_id, "invoice_number": "WS-EXPORT", "sale_date": "2026-10-15",
            "items": [{"product": self.product.id, "quantity": 2, "unit_price": "100.00"}],
        }, format="json")
        self.assertEqual(invoice.status_code, 201, invoice.data)
        self.client.post("/api/wholesale/returns/", {
            "invoice_item": invoice.data["items"][0]["id"], "quantity": 1,
            "amount": "100.00", "return_date": "2026-10-15",
        }, format="json")
        summary_export = self.client.get("/api/wholesale/summary/export/", {"search": "Test Buyer"})
        self.assertEqual(summary_export.status_code, 200)
        summary_sheet = load_workbook(BytesIO(summary_export.content), read_only=True)["All Parties Summary"]
        self.assertEqual(list(summary_sheet.iter_rows(values_only=True))[1][1], Decimal("100.00"))

    def test_failed_sale_rolls_back_invoice_and_stock(self):
        response = self.client.post("/api/wholesale/invoices/", {
            "party": self.party_id, "invoice_number": "WS-ROLLBACK", "sale_date": "2026-10-15",
            "items": [{"product": self.product.id, "quantity": 21, "unit_price": "100.00"}],
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.product.wholesale_sale_items.filter(invoice__invoice_number="WS-ROLLBACK").exists())
        self.factory_stock.refresh_from_db()
        self.assertEqual(self.factory_stock.quantity, 20)

    def test_payment_and_return_retries_are_idempotent(self):
        invoice = self.client.post("/api/wholesale/invoices/", {
            "party": self.party_id, "invoice_number": "WS-IDEMPOTENT", "sale_date": "2026-10-15",
            "items": [{"product": self.product.id, "quantity": 2, "unit_price": "100.00"}],
        }, format="json")
        payment_payload = {
            "invoice": invoice.data["id"], "payment_date": "2026-10-15", "bank_amount": "25.00",
            "bkash_amount": "0.00", "cash_amount": "0.00",
        }
        first_payment = self.client.post("/api/wholesale/payments/", payment_payload, format="json", HTTP_IDEMPOTENCY_KEY="pay-retry-1")
        retry_payment = self.client.post("/api/wholesale/payments/", payment_payload, format="json", HTTP_IDEMPOTENCY_KEY="pay-retry-1")
        self.assertEqual(first_payment.data["id"], retry_payment.data["id"])

        item_id = invoice.data["items"][0]["id"]
        return_payload = {"invoice_item": item_id, "quantity": 1, "amount": "100.00", "return_date": "2026-10-15"}
        first_return = self.client.post("/api/wholesale/returns/", return_payload, format="json", HTTP_IDEMPOTENCY_KEY="return-retry-1")
        retry_return = self.client.post("/api/wholesale/returns/", return_payload, format="json", HTTP_IDEMPOTENCY_KEY="return-retry-1")
        self.assertEqual(first_return.data["id"], retry_return.data["id"])
        self.factory_stock.refresh_from_db()
        self.assertEqual(self.factory_stock.quantity, 19)
        detail = self.client.get(f"/api/wholesale/invoices/{invoice.data['id']}/")
        self.assertEqual(detail.data["total_payments"], "25.00")
        self.assertEqual(detail.data["return_amount"], "100.00")