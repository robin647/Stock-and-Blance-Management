from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "role", "showroom", "is_active", "is_staff")
    list_filter = ("role", "showroom", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Showroom Info", {"fields": ("role", "showroom")}),
    )
