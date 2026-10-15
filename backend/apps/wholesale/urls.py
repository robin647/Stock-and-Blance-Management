from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    InvoiceViewSet, PartySummaryView, PartyViewSet, PaymentViewSet, ReturnViewSet,
    StockAdjustmentViewSet, WholesaleReportView,
)
from .excel_export import WholesaleExcelExportView

router = DefaultRouter()
router.register("parties", PartyViewSet, basename="wholesale-party")
router.register("invoices", InvoiceViewSet, basename="wholesale-invoice")
router.register("payments", PaymentViewSet, basename="wholesale-payment")
router.register("returns", ReturnViewSet, basename="wholesale-return")
router.register("stock-adjustments", StockAdjustmentViewSet, basename="stock-adjustment")

urlpatterns = [
    path("summary/", PartySummaryView.as_view(), name="wholesale-summary"),
    path("reports/", WholesaleReportView.as_view(), name="wholesale-reports"),
    path("reports/export/", WholesaleExcelExportView.as_view(), name="wholesale-export"),
] + router.urls