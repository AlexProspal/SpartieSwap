from django.contrib import admin

from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["listing", "borrower", "start_date", "end_date", "status"]
    list_filter = ["status"]
    search_fields = ["listing__title", "borrower__email", "borrower__display_name"]
