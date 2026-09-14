from django.core.validators import MinValueValidator
from django.db import models


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Product categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=150)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name="products")
    size = models.CharField(max_length=30, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "category", "size"], name="unique_product_variant")
        ]

    def __str__(self):
        return f"{self.name} ({self.size})" if self.size else self.name
