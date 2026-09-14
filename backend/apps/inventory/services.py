"""Transactional stock movement operations.

All changes to factory or showroom quantities must go through this module.
Locking the product row serializes concurrent movements of the same product,
including movements for different showrooms, so a factory quantity can never
be over-allocated.
"""

from django.db import transaction

from apps.products.models import Product

from .models import FactoryStock, ShowroomStock, StockTransfer


class InsufficientStock(Exception):
    """Raised when a requested movement exceeds the source stock."""


@transaction.atomic
def record_stock_transfer(*, showroom, product, transfer_type, quantity, date, notes, created_by):
    """Record one immutable movement and update its stock locations atomically."""
    # This lock is also important when a legacy product has no FactoryStock
    # record yet: only one request can create that record and move its stock.
    Product.objects.select_for_update().get(pk=product.pk)

    factory_stock, _ = FactoryStock.objects.get_or_create(
        product=product, defaults={"quantity": 0}
    )
    factory_stock = FactoryStock.objects.select_for_update().get(pk=factory_stock.pk)

    showroom_stock, _ = ShowroomStock.objects.get_or_create(
        showroom=showroom, product=product, defaults={"quantity": 0}
    )
    showroom_stock = ShowroomStock.objects.select_for_update().get(pk=showroom_stock.pk)

    if transfer_type == "receive":
        if factory_stock.quantity < quantity:
            raise InsufficientStock(
                f"Factory only has {factory_stock.quantity} units available. "
                f"Cannot receive {quantity} units."
            )
        factory_stock.quantity -= quantity
        showroom_stock.quantity += quantity
        factory_stock.save(update_fields=["quantity", "updated_at"])
        showroom_stock.save(update_fields=["quantity", "updated_at"])

    elif transfer_type == "sale":
        if showroom_stock.quantity < quantity:
            raise InsufficientStock(
                f"Cannot sell {quantity} units. Showroom only has "
                f"{showroom_stock.quantity} units in stock."
            )
        showroom_stock.quantity -= quantity
        showroom_stock.save(update_fields=["quantity", "updated_at"])

    elif transfer_type == "return":
        if showroom_stock.quantity < quantity:
            raise InsufficientStock(
                f"Cannot return {quantity} units. Showroom only has "
                f"{showroom_stock.quantity} units in stock."
            )
        showroom_stock.quantity -= quantity
        factory_stock.quantity += quantity
        showroom_stock.save(update_fields=["quantity", "updated_at"])
        factory_stock.save(update_fields=["quantity", "updated_at"])

    return StockTransfer.objects.create(
        showroom=showroom,
        product=product,
        transfer_type=transfer_type,
        quantity=quantity,
        date=date,
        notes=notes,
        created_by=created_by,
    )
