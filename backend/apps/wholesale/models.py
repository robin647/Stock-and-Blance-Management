from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.products.models import Product
from apps.showrooms.models import Showroom


class WholesaleParty(models.Model):
    name = models.CharField(max_length=180)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    business_name = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]

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
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_amount(self):
        return self.bank_amount + self.bkash_amount + self.cash_amount


class WholesaleReturn(models.Model):
    invoice_item = models.ForeignKey(WholesaleSaleItem, on_delete=models.PROTECT, related_name="returns")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    return_date = models.DateField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)