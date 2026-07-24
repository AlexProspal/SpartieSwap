from django import forms

from .models import Listing


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            "title",
            "description",
            "category",
            "condition",
            "pickup_area",
            "available_from",
            "available_until",
            "maximum_loan_days",
            "image",
        ]
        labels = {
            "title": "Item name",
            "pickup_area": "General pickup area",
            "maximum_loan_days": "Maximum loan length in days",
            "image": "Optional item image",
        }
        help_texts = {
            "maximum_loan_days": (
                "Enter the longest number of days one borrower may keep the item."
            ),
            "image": "The image is optional.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "available_from": forms.DateInput(attrs={"type": "date"}),
            "available_until": forms.DateInput(attrs={"type": "date"}),
            "maximum_loan_days": forms.NumberInput(attrs={"min": 1}),
        }
