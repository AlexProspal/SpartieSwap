from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from accounts.constants import CampusArea


class ItemCategory(models.TextChoices):
    COURSE_MATERIALS = "course_materials", "Course Materials"
    ELECTRONICS = "electronics", "Electronics"
    TOOLS = "tools", "Tools"
    KITCHEN_ITEMS = "kitchen_items", "Kitchen Items"
    CLOTHING = "clothing", "Clothing"
    RECREATION = "recreation", "Recreation"
    OTHER = "other", "Other"


class ItemCondition(models.TextChoices):
    NEW = "new", "New"
    LIKE_NEW = "like_new", "Like New"
    GOOD = "good", "Good"
    FAIR = "fair", "Fair"


class Listing(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
    )
    title = models.CharField(max_length=120)
    description = models.TextField()
    category = models.CharField(
        max_length=32,
        choices=ItemCategory.choices,
    )
    condition = models.CharField(
        max_length=20,
        choices=ItemCondition.choices,
    )
    pickup_area = models.CharField(
        max_length=32,
        choices=CampusArea.choices,
    )
    available_from = models.DateField()
    available_until = models.DateField()
    maximum_loan_days = models.PositiveIntegerField(
        default=7,
        validators=[MinValueValidator(1)],
        help_text="Longest number of days one borrower may keep the item.",
    )
    image = models.ImageField(
        upload_to="listing_images/",
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()

        if (
            self.available_from
            and self.available_until
            and self.available_from > self.available_until
        ):
            raise ValidationError(
                {
                    "available_until": (
                        "The availability end date must be on or after the start date."
                    )
                }
            )

        if (
            self.available_from
            and self.available_until
            and self.maximum_loan_days
            and self.available_from <= self.available_until
        ):
            availability_days = (self.available_until - self.available_from).days + 1
            if self.maximum_loan_days > availability_days:
                raise ValidationError(
                    {
                        "maximum_loan_days": (
                            "The maximum loan length cannot exceed the listing's "
                            "availability period."
                        )
                    }
                )
