from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from listings.models import Listing


class LoanStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    APPROVED = "approved", "Approved"
    PICKED_UP = "picked_up", "Picked Up"
    RETURNED = "returned", "Returned"
    COMPLETED = "completed", "Completed"
    DECLINED = "declined", "Declined"
    CANCELLED = "cancelled", "Cancelled"


# What the borrower is allowed to do, keyed by where the loan is now. The lessor
# side (approving, declining, confirming the return) lands in 1.4 and 1.6 - add
# a matching map there rather than widening this one, since these are the
# actions we let the borrower trigger.
BORROWER_TRANSITIONS = {
    LoanStatus.REQUESTED: {LoanStatus.CANCELLED},
    LoanStatus.APPROVED: {LoanStatus.PICKED_UP},
    LoanStatus.PICKED_UP: {LoanStatus.RETURNED},
}


LESSOR_TRANSITIONS = {
    LoanStatus.RETURNED: {LoanStatus.COMPLETED},
}


class Loan(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="loan_requests",
    )
    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrowing_requests",
    )
    start_date = models.DateField()
    return_date = models.DateField()
    message = models.TextField(
        blank=True,
        max_length=500,
        help_text="Optional message for coordinating the exchange.",
    )
    status = models.CharField(
        max_length=20,
        choices=LoanStatus.choices,
        default=LoanStatus.REQUESTED,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.listing.title} requested by {self.borrower}"

    def transition_to(self, status, transitions=BORROWER_TRANSITIONS):
        """Move the loan forward one step, refusing anything out of order.

        Keeps the buttons on the dashboard honest - someone can't skip from
        requested straight to returned by posting to the URL directly.
        """
        if status not in transitions.get(self.status, set()):
            raise ValidationError("This loan cannot be moved to that status.")
        self.status = status
        self.save(update_fields=["status", "updated_at"])

    @property
    def requested_days(self):
        if not self.start_date or not self.return_date:
            return None
        return (self.return_date - self.start_date).days + 1

    def clean(self):
        super().clean()
        errors = {}

        if self.listing_id:
            if not self.listing.is_active:
                errors["listing"] = "This listing is no longer active."

            if self.borrower_id and self.borrower_id == self.listing.owner_id:
                errors["borrower"] = "You cannot request your own listing."

        if self.start_date:
            if self.start_date < timezone.localdate():
                errors["start_date"] = "The start date cannot be in the past."
            elif (
                self.listing_id
                and self.start_date < self.listing.available_from
            ):
                errors["start_date"] = (
                    "The start date must fall within the listing's availability."
                )

        if self.start_date and self.return_date:
            if self.start_date > self.return_date:
                errors["return_date"] = (
                    "The return date must be on or after the start date."
                )
            elif (
                self.listing_id
                and self.return_date > self.listing.available_until
            ):
                errors["return_date"] = (
                    "The return date must fall within the listing's availability."
                )
            elif (
                self.listing_id
                and self.requested_days > self.listing.maximum_loan_days
            ):
                errors["return_date"] = (
                    "The requested loan exceeds this item's maximum loan length."
                )

        if errors:
            raise ValidationError(errors)
