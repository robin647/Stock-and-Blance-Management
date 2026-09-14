#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.products.models import Product
from apps.inventory.models import FactoryStock

# Initialize factory stock for all products
for product in Product.objects.all():
    factory_stock, created = FactoryStock.objects.get_or_create(product=product)
    if created:
        print(f"✓ Created factory stock for: {product.name}")
    else:
        print(f"✓ Factory stock already exists for: {product.name}")

print(f"\n✓ Factory stock initialized for {FactoryStock.objects.count()} products")
