from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.products.models import Product, ProductCategory
from apps.products.serializers import ProductSerializer
from apps.showrooms.models import Showroom

from .models import FactoryStock, ShowroomStock
from .services import InsufficientStock, record_stock_transfer


class InventoryTransferTests(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(name="Panjabi")
        self.product = Product.objects.create(
            name="Panjabi 42", category=category, selling_price=Decimal("1200.00")
        )
        FactoryStock.objects.create(product=self.product, quantity=500)
        self.showroom = Showroom.objects.create(name="Zone-1")

    def test_receive_sale_and_return_update_only_the_correct_locations(self):
        # A real user is required by the model, so use the database user table
        # only for the created_by value in this test.
        from apps.accounts.models import User
        user = User.objects.create_user(username="stock-admin", role="admin")

        def move(transfer_type, quantity):
            return record_stock_transfer(
                showroom=self.showroom,
                product=self.product,
                transfer_type=transfer_type,
                quantity=quantity,
                date=date.today(),
                notes="",
                created_by=user,
            )

        move("receive", 50)
        move("sale", 5)
        move("return", 10)

        self.assertEqual(FactoryStock.objects.get(product=self.product).quantity, 460)
        self.assertEqual(ShowroomStock.objects.get(showroom=self.showroom, product=self.product).quantity, 35)

        with self.assertRaises(InsufficientStock):
            move("receive", 461)
        self.assertEqual(FactoryStock.objects.get(product=self.product).quantity, 460)

    def test_product_creation_requires_and_creates_initial_factory_stock(self):
        serializer = ProductSerializer(data={
            "name": "Panjabi 44",
            "category": self.product.category_id,
            "size": "",
            "selling_price": "1300.00",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("initial_stock", serializer.errors)

        serializer = ProductSerializer(data={
            "name": "Panjabi 44",
            "category": self.product.category_id,
            "size": "",
            "selling_price": "1300.00",
            "initial_stock": 500,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()
        self.assertEqual(FactoryStock.objects.get(product=product).quantity, 500)

    def test_showroom_api_flow_returns_paginated_stock_and_dated_transfers(self):
        user = User.objects.create_user(
            username="zone-1-user", password="password", role="showroom_user", showroom=self.showroom
        )
        client = APIClient()
        client.force_authenticate(user=user)
        payload = {"product": self.product.id, "quantity": 20, "transfer_type": "receive", "date": "2026-09-13"}

        receive = client.post("/api/inventory/transfers/", payload, format="json")
        self.assertEqual(receive.status_code, 201, receive.data)
        self.assertEqual(FactoryStock.objects.get(product=self.product).quantity, 480)
        self.assertEqual(ShowroomStock.objects.get(showroom=self.showroom, product=self.product).quantity, 20)

        stocks = client.get("/api/inventory/showroom-stocks/")
        self.assertEqual(stocks.status_code, 200)
        self.assertEqual(stocks.data["results"][0]["quantity"], 20)

        transfers = client.get("/api/inventory/transfers/", {"date": "2026-09-13"})
        self.assertEqual(transfers.status_code, 200)
        transfer = transfers.data["results"][0]
        self.assertEqual(transfer["from_location"], "Factory/Main Stock")
        self.assertEqual(transfer["to_location"], "Zone-1")
        self.assertEqual(transfer["status"], "Completed")

        sale = client.post("/api/inventory/transfers/", {**payload, "quantity": 5, "transfer_type": "sale"}, format="json")
        self.assertEqual(sale.status_code, 201, sale.data)
        self.assertEqual(ShowroomStock.objects.get(showroom=self.showroom, product=self.product).quantity, 15)

        balance = client.post("/api/inventory/balances/", {
            "date": "2026-09-13", "cash_sale": "1000.00", "card_sale": "0.00",
            "expense": "0.00", "salary": "0.00", "deposit": "0.00",
        }, format="json")
        self.assertEqual(balance.status_code, 201, balance.data)

        report = client.get("/api/reports/daily/", {"date": "2026-09-13"})
        self.assertEqual(report.status_code, 200, report.data)
        self.assertEqual(report.data["stock"][0]["received"], 20)
        self.assertEqual(report.data["stock"][0]["sold"], 5)
        self.assertEqual(report.data["stock"][0]["closing"], 15)
        self.assertEqual(str(report.data["balance"]["cash_sale"]), "1000.00")
