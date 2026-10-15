from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from apps.inventory.models import FactoryStock, ShowroomStock, StockAdjustment
from apps.inventory.services import adjust_stock
from apps.products.models import Product

from .models import (
    WholesaleInvoice, WholesaleParty, WholesalePayment, WholesaleReturn, WholesaleSaleItem,
)


class PartySerializer(serializers.ModelSerializer):
    total_sales = serializers.SerializerMethodField()
    total_payments = serializers.SerializerMethodField()
    total_returns = serializers.SerializerMethodField()
    total_due = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()

    class Meta:
        model = WholesaleParty
        fields = ["id", "name", "phone", "address", "business_name", "notes", "is_active", "created_at",
                  "total_sales", "total_payments", "total_returns", "total_due", "total_credit"]
        read_only_fields = ["id", "created_at", "total_sales", "total_payments", "total_returns", "total_due", "total_credit"]

    def _totals(self, party):
        invoices = party.invoices.all()
        gross = sum((invoice.gross_amount for invoice in invoices), Decimal("0.00"))
        paid = sum((invoice.payment_total for invoice in invoices), Decimal("0.00"))
        returned = sum((invoice.return_total for invoice in invoices), Decimal("0.00"))
        due = sum((invoice.due_amount for invoice in invoices), Decimal("0.00"))
        credit = sum((invoice.credit_amount for invoice in invoices), Decimal("0.00"))
        return gross, paid, returned, due, credit

    def get_total_sales(self, party):
        return self._totals(party)[0]

    def get_total_payments(self, party):
        return self._totals(party)[1]

    def get_total_returns(self, party):
        return self._totals(party)[2]

    def get_total_due(self, party):
        return self._totals(party)[3]

    def get_total_credit(self, party):
        return self._totals(party)[4]


class WholesaleSaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    product_size = serializers.CharField(source="product.size", read_only=True)
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    returned_quantity = serializers.SerializerMethodField()
    returned_amount = serializers.SerializerMethodField()

    class Meta:
        model = WholesaleSaleItem
        fields = ["id", "product", "product_name", "product_code", "product_size", "quantity", "unit_price", "line_total", "returned_quantity", "returned_amount"]
        read_only_fields = ["id", "product_name", "product_code", "product_size", "line_total"]

    def get_returned_quantity(self, item):
        return item.returns.aggregate(value=Sum("quantity"))["value"] or 0

    def get_returned_amount(self, item):
        return item.returns.aggregate(value=Sum("amount"))["value"] or Decimal("0.00")


class PaymentSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = WholesalePayment
        fields = ["id", "payment_date", "bank_amount", "bkash_amount", "cash_amount", "total_amount", "notes", "created_at"]
        read_only_fields = ["id", "created_at", "total_amount"]


class ReturnSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice_item.invoice.invoice_number", read_only=True)
    product_name = serializers.CharField(source="invoice_item.product.name", read_only=True)

    class Meta:
        model = WholesaleReturn
        fields = ["id", "invoice_item", "invoice_number", "product_name", "quantity", "amount", "return_date", "notes", "created_at"]
        read_only_fields = ["id", "created_at", "invoice_number", "product_name"]

    def validate(self, attrs):
        item = attrs["invoice_item"]
        quantity = attrs["quantity"]
        amount = attrs["amount"]
        previous_returns = item.returns.aggregate(quantity=Sum("quantity"), amount=Sum("amount"))
        remaining_quantity = item.quantity - (previous_returns["quantity"] or 0)
        remaining_value = item.line_total - (previous_returns["amount"] or Decimal("0.00"))
        if quantity > remaining_quantity:
            raise serializers.ValidationError({"quantity": "Return quantity exceeds the eligible sold quantity."})
        if amount > remaining_value:
            raise serializers.ValidationError({"amount": "Return amount exceeds the remaining value of this item."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        item = WholesaleSaleItem.objects.select_related("invoice").select_for_update().get(
            pk=validated_data["invoice_item"].pk
        )
        invoice = item.invoice
        previous = item.returns.aggregate(quantity=Sum("quantity"), amount=Sum("amount"))
        if validated_data["quantity"] > item.quantity - (previous["quantity"] or 0):
            raise serializers.ValidationError({"quantity": "Return quantity exceeds the eligible sold quantity."})
        if validated_data["amount"] > item.line_total - (previous["amount"] or Decimal("0.00")):
            raise serializers.ValidationError({"amount": "Return amount exceeds the remaining value of this item."})
        location, showroom = invoice.stock_location, invoice.showroom
        stock = _get_location_stock(item.product, location, showroom, lock=True)
        stock.quantity += validated_data["quantity"]
        stock.save(update_fields=["quantity", "updated_at"])
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class InvoiceSerializer(serializers.ModelSerializer):
    items = WholesaleSaleItemSerializer(many=True)
    payments = PaymentSerializer(many=True, read_only=True)
    gross_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    total_payments = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    return_quantity = serializers.IntegerField(read_only=True)
    return_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    due_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    credit_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    return_history = serializers.SerializerMethodField()
    initial_bank_payment = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, default=0, write_only=True)
    initial_bkash_payment = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, default=0, write_only=True)
    initial_cash_payment = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, default=0, write_only=True)

    class Meta:
        model = WholesaleInvoice
        fields = ["id", "party", "party_name", "invoice_number", "sale_date", "stock_location", "showroom",
                  "notes", "items", "payments", "gross_amount", "total_quantity", "total_payments",
                  "return_quantity", "return_amount", "due_amount", "initial_bank_payment",
                  "initial_bkash_payment", "initial_cash_payment", "return_history", "credit_amount", "created_at"]
        read_only_fields = ["id", "party_name", "created_at", "gross_amount", "total_quantity", "total_payments",
                            "return_quantity", "return_amount", "due_amount"]

    party_name = serializers.CharField(source="party.name", read_only=True)

    def get_return_history(self, invoice):
        return [{
            "id": entry.id,
            "product_name": entry.invoice_item.product.name,
            "quantity": entry.quantity,
            "amount": entry.amount,
            "return_date": entry.return_date,
            "notes": entry.notes,
        } for item in invoice.items.all() for entry in item.returns.all()]

    def validate(self, attrs):
        location = attrs.get("stock_location", "factory")
        showroom = attrs.get("showroom")
        if location == "showroom" and not showroom:
            raise serializers.ValidationError({"showroom": "Select a showroom for showroom stock sales."})
        if location == "factory" and showroom:
            raise serializers.ValidationError({"showroom": "Factory invoices cannot select a showroom."})
        items = attrs.get("items")
        if not items:
            raise serializers.ValidationError({"items": "Add at least one product to the invoice."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")
        payment_amounts = {
            "bank_amount": validated_data.pop("initial_bank_payment", Decimal("0.00")),
            "bkash_amount": validated_data.pop("initial_bkash_payment", Decimal("0.00")),
            "cash_amount": validated_data.pop("initial_cash_payment", Decimal("0.00")),
        }
        if len({item["product"].pk for item in items_data}) != len(items_data):
            raise serializers.ValidationError({"items": "Each product can appear only once per invoice."})
        validated_data["created_by"] = self.context["request"].user
        invoice = WholesaleInvoice.objects.create(**validated_data)
        gross_amount = Decimal("0.00")
        location, showroom = invoice.stock_location, invoice.showroom
        for item_data in items_data:
            product = Product.objects.select_for_update().get(pk=item_data["product"].pk)
            stock = _get_location_stock(product, location, showroom, lock=True)
            if item_data["quantity"] > stock.quantity:
                raise serializers.ValidationError({"items": f"{product.name} has only {stock.quantity} units available at this location."})
            stock.quantity -= item_data["quantity"]
            stock.save(update_fields=["quantity", "updated_at"])
            item = WholesaleSaleItem.objects.create(invoice=invoice, product=product, **{
                "quantity": item_data["quantity"], "unit_price": item_data["unit_price"]
            })
            gross_amount += item.line_total
        total_payment = sum(payment_amounts.values())
        if total_payment > gross_amount:
            raise serializers.ValidationError({"initial_cash_payment": "Payments cannot exceed the invoice total."})
        if total_payment:
            WholesalePayment.objects.create(
                invoice=invoice, payment_date=invoice.sale_date, created_by=self.context["request"].user,
                **payment_amounts,
            )
        return invoice

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Invoices are immutable. Record a return or a new payment instead.")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.update({
            "gross_amount": instance.gross_amount,
            "total_quantity": instance.total_quantity,
            "total_payments": instance.payment_total,
            "return_quantity": instance.return_quantity,
            "return_amount": instance.return_total,
            "due_amount": instance.due_amount,
            "credit_amount": instance.credit_amount,
        })
        return data


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WholesalePayment
        fields = ["invoice", "payment_date", "bank_amount", "bkash_amount", "cash_amount", "notes"]

    def validate(self, attrs):
        if not (attrs["bank_amount"] + attrs["bkash_amount"] + attrs["cash_amount"]):
            raise serializers.ValidationError("A payment must have a positive amount.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        invoice = WholesaleInvoice.objects.select_for_update().get(pk=validated_data["invoice"].pk)
        total = validated_data["bank_amount"] + validated_data["bkash_amount"] + validated_data["cash_amount"]
        if total > invoice.due_amount:
            raise serializers.ValidationError({"invoice": "Payment exceeds the outstanding invoice due."})
        validated_data["invoice"] = invoice
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class StockAdjustmentSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = StockAdjustment
        fields = ["id", "product", "product_name", "location", "showroom", "showroom_name",
                  "previous_quantity", "new_quantity", "difference", "reason", "created_by_name", "created_at"]
        read_only_fields = ["id", "previous_quantity", "difference", "created_by_name", "created_at"]

    def validate(self, attrs):
        if attrs.get("location") == "showroom" and not attrs.get("showroom"):
            raise serializers.ValidationError({"showroom": "Select a showroom for this adjustment."})
        if attrs.get("location") == "factory" and attrs.get("showroom"):
            raise serializers.ValidationError({"showroom": "Factory adjustment cannot target a showroom."})
        if not attrs.get("reason", "").strip():
            raise serializers.ValidationError({"reason": "Enter a reason for the adjustment."})
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return adjust_stock(**validated_data)


def _get_location_stock(product, location, showroom=None, lock=False):
    if location == "factory":
        stock, _ = FactoryStock.objects.get_or_create(product=product, defaults={"quantity": 0})
        return FactoryStock.objects.select_for_update().get(pk=stock.pk) if lock else stock
    stock, _ = ShowroomStock.objects.get_or_create(showroom=showroom, product=product, defaults={"quantity": 0})
    return ShowroomStock.objects.select_for_update().get(pk=stock.pk) if lock else stock