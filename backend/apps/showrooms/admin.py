from django.contrib import admin

from .models import Showroom


@admin.register(Showroom)
class ShowroomAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
