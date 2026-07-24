from django import forms

from .models import Loan


class LoanRequestForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            "start_date",
            "return_date",
            "message",
        ]
        labels = {
            "start_date": "Start date",
            "return_date": "Return date",
            "message": "Coordination message",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "return_date": forms.DateInput(attrs={"type": "date"}),
            "message": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": (
                        "Optional: include a pickup-time preference or other "
                        "brief coordination details."
                    ),
                }
            ),
        }

    def __init__(self, *args, listing, borrower, **kwargs):
        self.listing = listing
        self.borrower = borrower
        super().__init__(*args, **kwargs)

        self.fields["start_date"].widget.attrs.update(
            {
                "min": listing.available_from.isoformat(),
                "max": listing.available_until.isoformat(),
            }
        )
        self.fields["return_date"].widget.attrs.update(
            {
                "min": listing.available_from.isoformat(),
                "max": listing.available_until.isoformat(),
            }
        )

    def _post_clean(self):
        self.instance.listing = self.listing
        self.instance.borrower = self.borrower
        super()._post_clean()
