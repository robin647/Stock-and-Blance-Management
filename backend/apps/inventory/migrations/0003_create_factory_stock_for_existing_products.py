from django.db import migrations


def create_missing_factory_stock(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    FactoryStock = apps.get_model("inventory", "FactoryStock")
    FactoryStock.objects.bulk_create(
        [FactoryStock(product=product, quantity=0) for product in Product.objects.all()],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [("inventory", "0002_factorystock_showroomstock_stocktransfer")]

    operations = [migrations.RunPython(create_missing_factory_stock, migrations.RunPython.noop)]
