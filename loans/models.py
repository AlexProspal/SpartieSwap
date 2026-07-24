from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from listings.models import Listing


class LoanStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    PICKED_UP = "PICKED_UP", "Picked Up"
    RETURNED = "RETURNED", "Returned"
    CANCELLED = "CANCELLED", "Cancelled"


class Loan(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="loans",
    )
    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loans",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=16,
        choices=LoanStatus.choices,
        default=LoanStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.listing} requested by {self.borrower}"

    def transition_to(self, status):
        allowed_transitions = {
            LoanStatus.PENDING: LoanStatus.CANCELLED,
            LoanStatus.APPROVED: LoanStatus.PICKED_UP,
            LoanStatus.PICKED_UP: LoanStatus.RETURNED,
        }
        if allowed_transitions.get(self.status) != status:
            raise ValidationError("This loan cannot be moved to that status.")
        self.status = status
        self.save(update_fields=["status", "updated_at"])
