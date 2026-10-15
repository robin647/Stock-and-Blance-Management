from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.products.models import Product
from apps.showrooms.models import Showroom


class WholesaleParty(models.Model):
    name = models.CharField(max_length=180)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    business_name = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [models.Index(fields=["name"]), models.Index(fields=["phone"])]

    def __str__(self):
        return self.name


class WholesaleInvoice(models.Model):
    LOCATION_CHOICES = [("factory", "Factory"), ("showroom", "Showroom")]

    party = models.ForeignKey(WholesaleParty, on_delete=models.PROTECT, related_name="invoices")
    invoice_number = models.CharField(max_length=80, unique=True)
    sale_date = models.DateField()
    stock_location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default="factory")
    showroom = models.ForeignKey(
        Showroom, null=True, blank=True, on_delete=models.PROTECT, related_name="wholesale_invoices"
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sale_date", "-id"]
        indexes = [models.Index(fields=["sale_date", "party"])]

    def __str__(self):
        return self.invoice_number

    @property
    def gross_amount(self):
        return sum((item.line_total for item in self.items.all()), start=0)

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def payment_total(self):
        return sum((payment.total_amount for payment in self.payments.all()), start=0)

    @property
    def return_total(self):
        return sum((entry.amount for item in self.items.all() for entry in item.returns.all()), start=0)

    @property
    def return_quantity(self):
        return sum(entry.quantity for item in self.items.all() for entry in item.returns.all())

    @property
    def due_amount(self):
        return max(0, self.gross_amount - self.return_total - self.payment_total)

    @property
    def credit_amount(self):
        return max(0, self.payment_total - (self.gross_amount - self.return_total))


class WholesaleSaleItem(models.Model):
    invoice = models.ForeignKey(WholesaleInvoice, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="wholesale_sale_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class WholesalePayment(models.Model):
    invoice = models.ForeignKey(WholesaleInvoice, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField()
    bank_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    bkash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    reference = models.CharField(max_length=120, blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["payment_date", "invoice"])]

    @property
    def total_amount(self):
        return self.bank_amount + self.bkash_amount + self.cash_amount


class WholesaleReturn(models.Model):
    invoice_item = models.ForeignKey(WholesaleSaleItem, on_delete=models.PROTECT, related_name="returns")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    return_date = models.DateField()
    notes = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["return_date", "invoice_item"])]


class EasyWholesaleSale(models.Model):
    STOCK_LOCATION_CHOICES = [("factory", "Factory"), ("showroom", "Showroom")]

    party = models.ForeignKey(WholesaleParty, on_delete=models.PROTECT, related_name="easy_sales")
    sale_date = models.DateField()
    bill_number = models.CharField(max_length=80, blank=True)
    product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.PROTECT, related_name="easy_wholesale_sales"
    )
    product_name = models.CharField(max_length=180, blank=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock_location = models.CharField(max_length=20, choices=STOCK_LOCATION_CHOICES, null=True, blank=True)
    showroom = models.ForeignKey(
        Showroom, null=True, blank=True, on_delete=models.PROTECT, related_name="easy_wholesale_sales"
    )
    notes = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sale_date", "-created_at", "-id"]
        indexes = [models.Index(fields=["party", "sale_date"]), models.Index(fields=["bill_number"])]
        constraints = [
            models.UniqueConstraint(
                fields=["bill_number"], condition=~models.Q(bill_number=""), name="unique_easy_wholesale_bill"
            )
        ]

    def __str__(self):
        return self.bill_number or f"Easy sale {self.pk}"


class EasyWholesalePayment(models.Model):
    party = models.ForeignKey(WholesaleParty, on_delete=models.PROTECT, related_name="easy_payments")
    payment_date = models.DateField()
    bank_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    bkash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-created_at", "-id"]
        indexes = [models.Index(fields=["party", "payment_date"])]

    @property
    def total_amount(self):
        return self.bank_amount + self.bkash_amount + self.cash_amount


class EasyWholesaleReturn(models.Model):
    party = models.ForeignKey(WholesaleParty, on_delete=models.PROTECT, related_name="easy_returns")
    return_date = models.DateField()
    original_bill_number = models.CharField(max_length=80, blank=True)
    easy_sale = models.ForeignKey(
        EasyWholesaleSale, null=True, blank=True, on_delete=models.PROTECT, related_name="returns"
    )
    product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.PROTECT, related_name="easy_wholesale_returns"
    )
    product_name = models.CharField(max_length=180, blank=True)
    stock_location = models.CharField(max_length=20, choices=EasyWholesaleSale.STOCK_LOCATION_CHOICES, null=True, blank=True)
    showroom = models.ForeignKey(
        Showroom, null=True, blank=True, on_delete=models.PROTECT, related_name="easy_wholesale_returns"
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-return_date", "-created_at", "-id"]
        indexes = [models.Index(fields=["party", "return_date"]), models.Index(fields=["original_bill_number"])]


class EasyWholesaleStockMovement(models.Model):
    MOVEMENT_CHOICES = [("sale", "Easy wholesale sale"), ("return", "Easy wholesale return")]

    movement_type = models.CharField(max_length=12, choices=MOVEMENT_CHOICES)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="easy_wholesale_stock_movements")
    stock_location = models.CharField(max_length=20, choices=EasyWholesaleSale.STOCK_LOCATION_CHOICES)
    showroom = models.ForeignKey(Showroom, null=True, blank=True, on_delete=models.PROTECT, related_name="easy_wholesale_stock_movements")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    movement_date = models.DateField()
    easy_sale = models.OneToOneField(
        EasyWholesaleSale, null=True, blank=True, on_delete=models.PROTECT, related_name="stock_movement"
    )
    easy_return = models.OneToOneField(
        EasyWholesaleReturn, null=True, blank=True, on_delete=models.PROTECT, related_name="stock_movement"
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-movement_date", "-created_at"]
        indexes = [models.Index(fields=["product", "movement_date"])]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(movement_type="sale", easy_sale__isnull=False, easy_return__isnull=True)
                    | models.Q(movement_type="return", easy_sale__isnull=True, easy_return__isnull=False)
                ),
                name="easy_stock_move_matches_transaction",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(stock_location="factory", showroom__isnull=True)
                    | models.Q(stock_location="showroom", showroom__isnull=False)
                ),
                name="easy_stock_move_valid_location",
            ),
        ]