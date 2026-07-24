from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SpartieUserAdmin(UserAdmin):
    list_display = ["email", "display_name", "campus_area", "is_staff"]
    search_fields = ["email", "display_name"]
    ordering = ["email"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Profile", {"fields": ["display_name", "campus_area"]}),
        ("Permissions", {"fields": ["is_active", "is_staff", "is_superuser", "groups"]}),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "display_name", "campus_area", "password1", "password2"],
            },
        ),
    ]
