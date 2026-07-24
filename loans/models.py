from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.formats import date_format

from listings.models import Listing


class LoanStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    APPROVED = "approved", "Approved"
    PICKED_UP = "picked_up", "Picked Up"
    RETURNED = "returned", "Returned"
    COMPLETED = "completed", "Completed"
    DECLINED = "declined", "Declined"
    CANCELLED = "cancelled", "Cancelled"


# Who is allowed to move a loan where, keyed by the status it is in now. Split by
# role so the borrower can't approve their own request and the lessor can't mark
# an item picked up on the borrower's behalf.
BORROWER_TRANSITIONS = {
    LoanStatus.REQUESTED: {LoanStatus.CANCELLED},
    LoanStatus.APPROVED: {LoanStatus.PICKED_UP},
    LoanStatus.PICKED_UP: {LoanStatus.RETURNED},
}

LESSOR_TRANSITIONS = {
    # Cancelling an approved loan is for when the lessor can no longer hand the
    # item over. Once it is picked up it is out in the world, so returning it is
    # the borrower's move, and confirming completion arrives with 1.6.
    LoanStatus.REQUESTED: {LoanStatus.APPROVED, LoanStatus.DECLINED},
    LoanStatus.APPROVED: {LoanStatus.CANCELLED},
}

# An approved or picked-up loan is holding the item; everything else has either
# not been agreed to or is already finished with it.
OCCUPYING_STATUSES = {LoanStatus.APPROVED, LoanStatus.PICKED_UP}


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

    def _move_to(self, status, allowed):
        """Move the loan one step, refusing anything out of order.

        Keeps the buttons honest - nobody can skip from requested straight to
        returned by posting at the URL directly.
        """
        if status not in allowed.get(self.status, set()):
            raise ValidationError("This loan cannot be moved to that status.")
        self.status = status
        self.save(update_fields=["status", "updated_at"])

    def borrower_transition_to(self, status):
        self._move_to(status, BORROWER_TRANSITIONS)

    def lessor_transition_to(self, status):
        # Approving is the one transition that depends on more than the current
        # status, since another loan may already have the item over these dates.
        if status == LoanStatus.APPROVED:
            conflict = self.conflicting_loan()
            if conflict is not None:
                raise ValidationError(
                    "These dates overlap an approved loan running "
                    f"{date_format(conflict.start_date, 'DATE_FORMAT')} to "
                    f"{date_format(conflict.return_date, 'DATE_FORMAT')}."
                )
        self._move_to(status, LESSOR_TRANSITIONS)

    def conflicting_loan(self):
        """The already-approved loan whose dates clash with this one, if any.

        Dates are inclusive at both ends: someone keeping an item until the 24th
        still has it on the 24th, so the next loan can only start on the 25th.
        Two loans overlap when each one starts on or before the other ends.
        """
        return (
            Loan.objects.filter(
                listing_id=self.listing_id,
                status__in=OCCUPYING_STATUSES,
                start_date__lte=self.return_date,
                return_date__gte=self.start_date,
            )
            .exclude(pk=self.pk)
            .order_by("start_date")
            .first()
        )

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
