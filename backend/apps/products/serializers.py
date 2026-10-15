from rest_framework import serializers
from django.db import transaction

from .models import Product, ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    initial_stock = serializers.IntegerField(min_value=0, write_only=True, required=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "code", "category", "category_name", "size",
            "selling_price", "is_active", "initial_stock", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Selling price cannot be negative.")
        return value

    def validate_code(self, value):
        if not value:
            return None
        duplicates = Product.objects.filter(code=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A product with this code already exists.")
        return value

    def validate(self, attrs):
        if self.instance and "initial_stock" in attrs:
            raise serializers.ValidationError({
                "initial_stock": "Initial stock can only be set when creating a product."
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        # Initial stock always starts at the factory; it is never copied to a
        # showroom until an explicit receive transfer is recorded.
        initial_stock = validated_data.pop("initial_stock")
        product = Product.objects.create(**validated_data)

        # Imported lazily to keep the product app independent during startup.
        from apps.inventory.models import FactoryStock
        FactoryStock.objects.create(product=product, quantity=initial_stock)
        return product
