from rest_framework.routers import DefaultRouter

from .views import (
    DailyBalanceViewSet,
    DailyStockViewSet,
    FactoryStockViewSet,
    ShowroomStockViewSet,
    StockTransferViewSet,
)

router = DefaultRouter()
router.register("factory-stocks", FactoryStockViewSet, basename="factory-stock")
router.register("showroom-stocks", ShowroomStockViewSet, basename="showroom-stock")
router.register("transfers", StockTransferViewSet, basename="stock-transfer")
router.register("stocks", DailyStockViewSet, basename="daily-stock")
router.register("balances", DailyBalanceViewSet, basename="daily-balance")

urlpatterns = router.urls
