from django import forms
from django.db.models import Q

from accounts.constants import CampusArea

from .models import ItemCategory, ItemCondition, Listing


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


def _any(label, choices):
    """Choice list with a blank 'no preference' option in front."""
    return [("", label), *choices]


class ListingFilterForm(forms.Form):
    """Search and filter controls for the browse page (Figure 3).

    Submitted with GET rather than POST so a filtered browse page can be
    bookmarked, shared, and reloaded with the back button.
    """

    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={"placeholder": "Search by item name or description"}
        ),
    )
    category = forms.ChoiceField(
        required=False,
        label="Category",
        choices=lambda: _any("Any category", ItemCategory.choices),
    )
    condition = forms.ChoiceField(
        required=False,
        label="Condition",
        choices=lambda: _any("Any condition", ItemCondition.choices),
    )
    pickup_area = forms.ChoiceField(
        required=False,
        label="Pickup area",
        choices=lambda: _any("Any pickup area", CampusArea.choices),
    )
    available_from = forms.DateField(
        required=False,
        label="Needed from",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    available_until = forms.DateField(
        required=False,
        label="Needed until",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field, forms.ChoiceField) else "form-control"
            field.widget.attrs.setdefault("class", css)

    def clean_q(self):
        # Collapse surrounding whitespace so " drill " and "drill" behave the same
        # and a box containing only spaces counts as empty.
        return self.cleaned_data.get("q", "").strip()

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("available_from"), cleaned.get("available_until")
        if start and end and start > end:
            self.add_error(
                "available_until",
                "The end of the range must be on or after the start.",
            )
        return cleaned

    @property
    def is_filtered(self):
        """True when the user actually narrowed something down.

        Lets the page tell "nothing matched your search" apart from "nobody has
        listed anything yet", which are very different messages to show.
        """
        if not self.is_bound:
            return False
        if not self.is_valid():
            # A bad date range still means they were trying to filter.
            return any(self.data.get(name) for name in self.fields)
        return any(self.cleaned_data.get(name) for name in self.fields)

    def apply(self, listings):
        """Narrow a Listing queryset by whatever the user filled in.

        An unbound or invalid form returns the queryset untouched, so a bad date
        range shows an error next to the field rather than an empty page.
        """
        if not self.is_bound or not self.is_valid():
            return listings

        data = self.cleaned_data

        if term := data.get("q"):
            listings = listings.filter(
                Q(title__icontains=term) | Q(description__icontains=term)
            )

        for field in ("category", "condition", "pickup_area"):
            if value := data.get(field):
                listings = listings.filter(**{field: value})

        # Availability is "can I actually borrow it then", so each date the user
        # gives has to fall inside the listing's window. Applying both narrows to
        # windows that cover the whole range, which matches the rule a request is
        # validated against later - no point offering dates that would be
        # rejected at request time.
        if start := data.get("available_from"):
            listings = listings.filter(
                available_from__lte=start, available_until__gte=start
            )
        if end := data.get("available_until"):
            listings = listings.filter(
                available_from__lte=end, available_until__gte=end
            )

        return listings
