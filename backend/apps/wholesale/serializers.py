from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from apps.inventory.models import FactoryStock, ShowroomStock, StockAdjustment
from apps.inventory.services import adjust_stock
from apps.products.models import Product

from .models import (
    EasyWholesalePayment, EasyWholesaleReturn, EasyWholesaleSale,
    WholesaleInvoice, WholesaleParty, WholesalePayment, WholesaleReturn, WholesaleSaleItem,
)
from .services import record_easy_stock_movement


class PartySerializer(serializers.ModelSerializer):
    total_sales = serializers.SerializerMethodField()
    total_payments = serializers.SerializerMethodField()
    total_returns = serializers.SerializerMethodField()
    total_due = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()

    class Meta:
        model = WholesaleParty
        fields = ["id", "name", "contact_person", "phone", "address", "business_name", "notes", "is_active", "created_at",
                  "total_sales", "total_payments", "total_returns", "total_due", "total_credit"]
        read_only_fields = ["id", "created_at", "total_sales", "total_payments", "total_returns", "total_due", "total_credit"]

    def _totals(self, party):
        cached = getattr(self, "_party_totals_cache", None)
        if cached is None:
            cached = self._party_totals_cache = {}
        if party.pk in cached:
            return cached[party.pk]
        supplied_totals = self.context.get("party_totals", {}).get(party.pk)
        if supplied_totals:
            totals = (
                supplied_totals["total_sales"], supplied_totals["total_payments"],
                supplied_totals["total_returns"], supplied_totals["total_due"],
                supplied_totals["total_credit"],
            )
            cached[party.pk] = totals
            return totals
        invoices = party.invoices.all()
        gross = sum((invoice.gross_amount for invoice in invoices), Decimal("0.00"))
        paid = sum((invoice.payment_total for invoice in invoices), Decimal("0.00"))
        returned = sum((invoice.return_total for invoice in invoices), Decimal("0.00"))
        due = sum((invoice.due_amount for invoice in invoices), Decimal("0.00"))
        credit = sum((invoice.credit_amount for invoice in invoices), Decimal("0.00"))
        easy_sales = party.easy_sales.aggregate(gross=Sum("total_amount"), quantity=Sum("quantity"))
        easy_payments = party.easy_payments.aggregate(bank=Sum("bank_amount"), bkash=Sum("bkash_amount"), cash=Sum("cash_amount"))
        easy_returns = party.easy_returns.aggregate(amount=Sum("amount"))
        easy_gross = easy_sales["gross"] or Decimal("0.00")
        easy_paid = sum((easy_payments[key] or Decimal("0.00") for key in ("bank", "bkash", "cash")), Decimal("0.00"))
        easy_returned = easy_returns["amount"] or Decimal("0.00")
        easy_balance = easy_gross - easy_paid - easy_returned
        totals = (gross - returned + easy_gross - easy_returned, paid + easy_paid, returned + easy_returned,
              due + max(Decimal("0.00"), easy_balance), credit + max(Decimal("0.00"), -easy_balance))
        cached[party.pk] = totals
        return totals

    def validate_name(self, value):
        duplicates = WholesaleParty.objects.filter(name__iexact=value.strip())
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A party with this name already exists.")
        return value.strip()

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
        fields = ["id", "payment_date", "bank_amount", "bkash_amount", "cash_amount", "total_amount", "reference", "notes", "created_at"]
        read_only_fields = ["id", "created_at", "total_amount"]


class ReturnSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice_item.invoice.invoice_number", read_only=True)
    product_name = serializers.CharField(source="invoice_item.product.name", read_only=True)

    class Meta:
        model = WholesaleReturn
        fields = ["id", "invoice_item", "invoice_number", "product_name", "quantity", "amount", "return_date", "notes", "created_at"]
        read_only_fields = ["id", "created_at", "invoice_number", "product_name"]

    def validate(self, attrs):
        request = self.context.get("request")
        idempotency_key = request.headers.get("Idempotency-Key") if request else None
        if idempotency_key:
            if len(idempotency_key) > 64:
                raise serializers.ValidationError({"detail": "Idempotency-Key must be 64 characters or fewer."})
            existing = WholesaleReturn.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                if existing.invoice_item_id != attrs["invoice_item"].pk:
                    raise serializers.ValidationError({"detail": "Idempotency-Key was already used for another return."})
                self.context["existing_return"] = existing
                return attrs
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
        if amount != item.unit_price * quantity:
            raise serializers.ValidationError({"amount": "Return amount must use the original sale unit price."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        if self.context.get("existing_return"):
            return self.context["existing_return"]
        item = WholesaleSaleItem.objects.select_related("invoice").select_for_update().get(
            pk=validated_data["invoice_item"].pk
        )
        idempotency_key = self.context["request"].headers.get("Idempotency-Key")
        if idempotency_key:
            existing = WholesaleReturn.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing
        invoice = item.invoice
        previous = item.returns.aggregate(quantity=Sum("quantity"), amount=Sum("amount"))
        if validated_data["quantity"] > item.quantity - (previous["quantity"] or 0):
            raise serializers.ValidationError({"quantity": "Return quantity exceeds the eligible sold quantity."})
        if validated_data["amount"] > item.line_total - (previous["amount"] or Decimal("0.00")):
            raise serializers.ValidationError({"amount": "Return amount exceeds the remaining value of this item."})
        if validated_data["amount"] != item.unit_price * validated_data["quantity"]:
            raise serializers.ValidationError({"amount": "Return amount must use the original sale unit price."})
        location, showroom = invoice.stock_location, invoice.showroom
        stock = _get_location_stock(item.product, location, showroom, lock=True)
        stock.quantity += validated_data["quantity"]
        stock.save(update_fields=["quantity", "updated_at"])
        validated_data["created_by"] = self.context["request"].user
        validated_data["idempotency_key"] = idempotency_key or None
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
        party = attrs.get("party")
        if party and not party.is_active:
            raise serializers.ValidationError({"party": "Inactive parties cannot be used for new sales."})
        bill_number = attrs.get("invoice_number")
        if bill_number and EasyWholesaleSale.objects.filter(bill_number__iexact=bill_number).exists():
            raise serializers.ValidationError({"invoice_number": "This cash memo number is already used by an Easy wholesale sale."})
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
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = WholesalePayment
        fields = ["id", "invoice", "payment_date", "bank_amount", "bkash_amount", "cash_amount",
                  "total_amount", "reference", "notes", "created_at"]
        read_only_fields = ["id", "total_amount", "created_at"]

    def validate(self, attrs):
        if not (attrs["bank_amount"] + attrs["bkash_amount"] + attrs["cash_amount"]):
            raise serializers.ValidationError("A payment must have a positive amount.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        invoice = WholesaleInvoice.objects.select_for_update().get(pk=validated_data["invoice"].pk)
        idempotency_key = self.context["request"].headers.get("Idempotency-Key")
        if idempotency_key:
            if len(idempotency_key) > 64:
                raise serializers.ValidationError({"detail": "Idempotency-Key must be 64 characters or fewer."})
            existing = WholesalePayment.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                if existing.invoice_id != invoice.pk:
                    raise serializers.ValidationError({"detail": "Idempotency-Key was already used for another payment."})
                return existing
        total = validated_data["bank_amount"] + validated_data["bkash_amount"] + validated_data["cash_amount"]
        if total > invoice.due_amount:
            raise serializers.ValidationError({"invoice": "Payment exceeds the outstanding invoice due."})
        validated_data["invoice"] = invoice
        validated_data["created_by"] = self.context["request"].user
        validated_data["idempotency_key"] = idempotency_key or None
        return super().create(validated_data)


class EasyWholesaleSaleSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source="party.name", read_only=True)
    product_label = serializers.SerializerMethodField()

    class Meta:
        model = EasyWholesaleSale
        fields = ["id", "party", "party_name", "sale_date", "bill_number", "product", "product_name",
                  "product_label", "quantity", "total_amount", "stock_location", "showroom", "notes", "created_at"]
        read_only_fields = ["id", "party_name", "product_label", "created_at"]

    def get_product_label(self, sale):
        return sale.product.name if sale.product else sale.product_name

    def validate(self, attrs):
        party = attrs.get("party")
        if party and not party.is_active:
            raise serializers.ValidationError({"party": "Inactive parties cannot be used for new sales."})
        bill_number = attrs.get("bill_number", "").strip()
        if bill_number and WholesaleInvoice.objects.filter(invoice_number__iexact=bill_number).exists():
            raise serializers.ValidationError({"bill_number": "This cash memo number already exists in Wholesale Sales."})
        if bill_number:
            attrs["bill_number"] = bill_number
        product = attrs.get("product")
        location = attrs.get("stock_location")
        showroom = attrs.get("showroom")
        if location == "showroom" and not showroom:
            raise serializers.ValidationError({"showroom": "Choose a showroom when using showroom stock."})
        if location == "factory" and showroom:
            raise serializers.ValidationError({"showroom": "Factory stock sales cannot specify a showroom."})
        if location and not product:
            raise serializers.ValidationError({"product": "Select a real product before changing inventory."})
        if not product and location:
            raise serializers.ValidationError({"stock_location": "A financial-only sale must not select an inventory location."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        key = request.headers.get("Idempotency-Key")
        if key:
            if len(key) > 64:
                raise serializers.ValidationError({"detail": "Idempotency-Key must be 64 characters or fewer."})
            existing = EasyWholesaleSale.objects.filter(idempotency_key=key).first()
            if existing:
                comparable_fields = ["sale_date", "bill_number", "product_name", "quantity", "total_amount", "stock_location", "notes"]
                same_payload = existing.party_id == validated_data["party"].pk and existing.product_id == getattr(validated_data.get("product"), "pk", None)
                same_payload = same_payload and existing.showroom_id == getattr(validated_data.get("showroom"), "pk", None)
                same_payload = same_payload and all(getattr(existing, field) == validated_data.get(field, getattr(existing, field)) for field in comparable_fields)
                if not same_payload:
                    raise serializers.ValidationError({"detail": "Idempotency-Key was already used for a different sale."})
                return existing
        validated_data["created_by"] = request.user
        validated_data["idempotency_key"] = key or None
        product = validated_data.get("product")
        sale = super().create(validated_data)
        if product and sale.stock_location:
            try:
                record_easy_stock_movement(
                    movement_type="sale", product=product, stock_location=sale.stock_location,
                    showroom=sale.showroom, quantity=sale.quantity, movement_date=sale.sale_date,
                    user=request.user, sale=sale, notes=sale.notes,
                )
            except ValueError as error:
                raise serializers.ValidationError({"quantity": str(error)}) from error
        return sale

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Saved easy sales are immutable; use an audited correction workflow.")


class EasyWholesalePaymentSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source="party.name", read_only=True)
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = EasyWholesalePayment
        fields = ["id", "party", "party_name", "payment_date", "bank_amount", "bkash_amount", "cash_amount",
                  "total_amount", "reference", "notes", "created_at"]
        read_only_fields = ["id", "party_name", "total_amount", "created_at"]

    def validate(self, attrs):
        if not any(attrs.get(field, Decimal("0")) > 0 for field in ("bank_amount", "bkash_amount", "cash_amount")):
            raise serializers.ValidationError({"total_amount": "Enter a positive amount in at least one payment method."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        key = request.headers.get("Idempotency-Key")
        if key:
            if len(key) > 64:
                raise serializers.ValidationError({"detail": "Idempotency-Key must be 64 characters or fewer."})
            existing = EasyWholesalePayment.objects.filter(idempotency_key=key).first()
            if existing:
                same_payload = existing.party_id == validated_data["party"].pk and all(
                    getattr(existing, field) == validated_data.get(field, getattr(existing, field))
                    for field in ["payment_date", "bank_amount", "bkash_amount", "cash_amount", "reference", "notes"]
                )
                if not same_payload:
                    raise serializers.ValidationError({"detail": "Idempotency-Key was already used for a different payment."})
                return existing
        validated_data["created_by"] = request.user
        validated_data["idempotency_key"] = key or None
        return super().create(validated_data)

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Saved easy payments are immutable.")


class EasyWholesaleReturnSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source="party.name", read_only=True)
    product_label = serializers.SerializerMethodField()

    class Meta:
        model = EasyWholesaleReturn
        fields = ["id", "party", "party_name", "return_date", "original_bill_number", "easy_sale", "product",
                  "product_name", "product_label", "quantity", "amount", "stock_location", "showroom", "notes", "created_at"]
        read_only_fields = ["id", "party_name", "product_label", "created_at"]

    def get_product_label(self, return_record):
        if return_record.product:
            return return_record.product.name
        if return_record.easy_sale and return_record.easy_sale.product:
            return return_record.easy_sale.product.name
        return return_record.product_name or (return_record.easy_sale.product_name if return_record.easy_sale else "")

    def validate(self, attrs):
        sale = attrs.get("easy_sale")
        party = attrs.get("party")
        if sale and party and sale.party_id != party.pk:
            raise serializers.ValidationError({"easy_sale": "The selected sale belongs to a different party."})
        if sale and attrs.get("product") and sale.product_id != attrs["product"].pk:
            raise serializers.ValidationError({"product": "The returned product must match the selected sale."})
        location = attrs.get("stock_location")
        showroom = attrs.get("showroom")
        if location == "showroom" and not showroom:
            raise serializers.ValidationError({"showroom": "Choose a showroom for the physical return."})
        if location == "factory" and showroom:
            raise serializers.ValidationError({"showroom": "Factory returns cannot specify a showroom."})
        if location and not attrs.get("product") and not (sale and sale.product):
            raise serializers.ValidationError({"product": "Select the physical product before restoring stock."})
        if sale:
            attrs.setdefault("product", sale.product)
            attrs.setdefault("product_name", sale.product_name)
            if not attrs.get("original_bill_number"):
                attrs["original_bill_number"] = sale.bill_number
            attrs["stock_location"] = sale.stock_location
            attrs["showroom"] = sale.showroom
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        key = request.headers.get("Idempotency-Key")
        if key:
            if len(key) > 64:
                raise serializers.ValidationError({"detail": "Idempotency-Key must be 64 characters or fewer."})
            existing = EasyWholesaleReturn.objects.filter(idempotency_key=key).first()
            if existing:
                same_payload = existing.party_id == validated_data["party"].pk and all(
                    getattr(existing, field) == validated_data.get(field, getattr(existing, field))
                    for field in ["return_date", "original_bill_number", "quantity", "amount", "product_name", "notes", "stock_location"]
                )
                same_payload = same_payload and existing.easy_sale_id == getattr(validated_data.get("easy_sale"), "pk", None)
                same_payload = same_payload and existing.product_id == getattr(validated_data.get("product"), "pk", None)
                same_payload = same_payload and existing.showroom_id == getattr(validated_data.get("showroom"), "pk", None)
                if not same_payload:
                    raise serializers.ValidationError({"detail": "Idempotency-Key was already used for a different return."})
                return existing
        sale = validated_data.get("easy_sale")
        if sale:
            sale = EasyWholesaleSale.objects.select_for_update().get(pk=sale.pk)
            prior_returns = sale.returns.aggregate(quantity=Sum("quantity"), amount=Sum("amount"))
            already_returned = prior_returns["quantity"] or 0
            if validated_data["quantity"] > sale.quantity - already_returned:
                raise serializers.ValidationError({"quantity": "Return quantity exceeds the eligible sale quantity."})
            if validated_data["amount"] > sale.total_amount - (prior_returns["amount"] or Decimal("0")):
                raise serializers.ValidationError({"amount": "Return amount exceeds the remaining sale value."})
        validated_data["created_by"] = request.user
        validated_data["idempotency_key"] = key or None
        return_record = super().create(validated_data)
        location = return_record.stock_location
        showroom = return_record.showroom
        product_value = return_record.product or (sale.product if sale else None)
        if product_value and location:
            try:
                record_easy_stock_movement(
                    movement_type="return", product=product_value, stock_location=location,
                    showroom=showroom, quantity=return_record.quantity,
                    movement_date=return_record.return_date, user=request.user,
                    return_record=return_record, notes=return_record.notes,
                )
            except ValueError as error:
                raise serializers.ValidationError({"quantity": str(error)}) from error
        return return_record

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Saved easy returns are immutable.")


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