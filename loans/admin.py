from django.contrib import admin

from .models import Loan, Review


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


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "loan",
        "reviewer",
        "reviewee",
        "rating",
        "created_at",
    ]
    list_filter = ["rating", "created_at"]
    search_fields = [
        "loan__listing__title",
        "reviewer__email",
        "reviewer__display_name",
        "reviewee__email",
        "reviewee__display_name",
        "comment",
    ]
    ordering = ["-created_at"]
