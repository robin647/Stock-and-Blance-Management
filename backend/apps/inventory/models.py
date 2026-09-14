from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.products.models import Product
from apps.showrooms.models import Showroom


class FactoryStock(models.Model):
    """
    Global factory inventory for each product.
    Decreases when showrooms receive products, increases when showrooms return.
    """

    product = models.OneToOneField(Product, on_delete=models.PROTECT, related_name="factory_stock")
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Factory: {self.product.name} ({self.quantity} units)"

    class Meta:
        verbose_name = "Factory Stock"
        verbose_name_plural = "Factory Stock"


class ShowroomStock(models.Model):
    """
    Current inventory for each showroom-product combination.
    Increases when showroom receives from factory or through returns.
    Decreases when showroom sells or returns to factory.
    """

    showroom = models.ForeignKey(Showroom, on_delete=models.PROTECT, related_name="stocks")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="showroom_stocks")
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("showroom", "product")
        ordering = ["showroom", "product"]
        verbose_name = "Showroom Stock"
        verbose_name_plural = "Showroom Stocks"

    def __str__(self):
        return f"{self.showroom.name}: {self.product.name} ({self.quantity} units)"


class StockTransfer(models.Model):
    """
    Audit trail of all stock movements (receives, sales, returns).
    Used to track inventory changes and maintain history.
    """

    TRANSFER_TYPE_CHOICES = [
        ("receive", "Receive from Factory"),
        ("sale", "Sale to Customer"),
        ("return", "Return to Factory"),
    ]

    showroom = models.ForeignKey(Showroom, on_delete=models.PROTECT, related_name="stock_transfers")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_transfers")
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["showroom", "date"]),
            models.Index(fields=["product", "date"]),
        ]

    def __str__(self):
        return f"{self.showroom.name} - {self.get_transfer_type_display()} - {self.product.name} ({self.quantity})"


class DailyStock(models.Model):
    """
    One row per (showroom, product, date).
    closing_qty = opening_qty + received_qty - sold_qty + return_qty
    Enforced by full_clean() before every save — see clean().
    """

    showroom = models.ForeignKey(Showroom, on_delete=models.PROTECT, related_name="daily_stocks")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="daily_stocks")
    date = models.DateField()

    opening_qty = models.PositiveIntegerField(default=0)
    received_qty = models.PositiveIntegerField(default=0)
    sold_qty = models.PositiveIntegerField(default=0)
    return_qty = models.PositiveIntegerField(default=0)
    closing_qty = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "product__name"]
        constraints = [
            models.UniqueConstraint(fields=["showroom", "product", "date"], name="unique_daily_stock_entry")
        ]

    def __str__(self):
        return f"{self.showroom} / {self.product} / {self.date}"

    def compute_closing(self):
        return self.opening_qty + self.received_qty - self.sold_qty + self.return_qty

    def clean(self):
        from django.core.exceptions import ValidationError

        closing = self.compute_closing()
        if closing < 0:
            raise ValidationError(
                "Closing stock cannot be negative. Sold quantity exceeds available stock "
                f"(opening {self.opening_qty} + received {self.received_qty} + return {self.return_qty})."
            )

    def save(self, *args, **kwargs):
        self.closing_qty = self.compute_closing()
        self.full_clean()
        super().save(*args, **kwargs)


class DailyBalance(models.Model):
    """
    One row per (showroom, date).
    total_sale = cash_sale + card_sale
    closing_balance = opening_balance + cash_sale - expense - salary - deposit
    (card_sale counts toward total_sale but NOT toward cash closing_balance)
    """

    showroom = models.ForeignKey(Showroom, on_delete=models.PROTECT, related_name="daily_balances")
    date = models.DateField()

    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cash_sale = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    card_sale = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_sale = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expense = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["showroom", "date"], name="unique_daily_balance_entry")
        ]

    def __str__(self):
        return f"{self.showroom} / {self.date}"

    def compute_totals(self):
        total_sale = self.cash_sale + self.card_sale
        closing_balance = self.opening_balance + self.cash_sale - self.expense - self.salary - self.deposit
        return total_sale, closing_balance

    def clean(self):
        from django.core.exceptions import ValidationError

        _, closing_balance = self.compute_totals()
        if closing_balance < 0:
            raise ValidationError(
                "Closing balance would be negative. Check expense, salary, and deposit amounts "
                "against opening balance and cash sale."
            )

    def save(self, *args, **kwargs):
        self.total_sale, self.closing_balance = self.compute_totals()
        self.full_clean()
        super().save(*args, **kwargs)
