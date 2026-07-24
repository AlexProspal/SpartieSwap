from django.contrib import admin

from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "owner",
        "category",
        "condition",
        "pickup_area",
        "available_from",
        "available_until",
        "maximum_loan_days",
        "is_active",
    ]
    list_filter = [
        "is_active",
        "category",
        "condition",
        "pickup_area",
    ]
    search_fields = [
        "title",
        "description",
        "owner__email",
        "owner__display_name",
    ]
