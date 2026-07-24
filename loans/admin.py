from django.contrib import admin

from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = [
        "listing",
        "borrower",
        "start_date",
        "return_date",
        "status",
        "requested_at",
    ]
    list_filter = ["status", "start_date", "return_date"]
    search_fields = [
        "listing__title",
        "borrower__email",
        "borrower__display_name",
        "message",
    ]
    ordering = ["-requested_at"]
