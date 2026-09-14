from django.contrib import admin

from .models import DailyBalance, DailyStock


@admin.register(DailyStock)
class DailyStockAdmin(admin.ModelAdmin):
    list_display = ("showroom", "product", "date", "opening_qty", "received_qty", "sold_qty", "return_qty", "closing_qty")
    list_filter = ("showroom", "date")
    search_fields = ("product__name",)


@admin.register(DailyBalance)
class DailyBalanceAdmin(admin.ModelAdmin):
    list_display = ("showroom", "date", "opening_balance", "cash_sale", "card_sale", "total_sale", "closing_balance")
    list_filter = ("showroom", "date")
