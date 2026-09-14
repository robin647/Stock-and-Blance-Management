from django.urls import path

from .excel_export import DailyExcelExportView, MonthlyExcelExportView
from .views import DailyStatementView, DashboardView, MonthlyReportView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("daily/", DailyStatementView.as_view(), name="daily-statement"),
    path("monthly/", MonthlyReportView.as_view(), name="monthly-report"),
    path("export/daily/", DailyExcelExportView.as_view(), name="export-daily"),
    path("export/monthly/", MonthlyExcelExportView.as_view(), name="export-monthly"),
]
