from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.constants import CampusArea
from listings.models import ItemCategory, ItemCondition, Listing

from .models import Loan, LoanStatus


class LoanRequestTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.lessor = user_model.objects.create_user(
            email="lessor@case.edu",
            password="TestPassword123!",
            display_name="Test Lessor",
        )
        self.borrower = user_model.objects.create_user(
            email="borrower@case.edu",
            password="TestPassword123!",
            display_name="Test Borrower",
        )
        self.other_lessor = user_model.objects.create_user(
            email="other-lessor@case.edu",
            password="TestPassword123!",
            display_name="Other Lessor",
        )

        today = timezone.localdate()
        self.listing = Listing.objects.create(
            owner=self.lessor,
            title="TI-84 Calculator",
            description="A calculator available for exams.",
            category=ItemCategory.COURSE_MATERIALS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=today + timedelta(days=1),
            available_until=today + timedelta(days=10),
            maximum_loan_days=4,
            is_active=True,
        )
        self.request_url = reverse(
            "loans:request-listing",
            kwargs={"listing_pk": self.listing.pk},
        )

    def valid_request_data(self):
        return {
            "start_date": self.listing.available_from.isoformat(),
            "return_date": (
                self.listing.available_from + timedelta(days=2)
            ).isoformat(),
            "message": "Could I pick this up near the library?",
        }

    def test_request_page_requires_login(self):
        response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_item_detail_links_to_request_page_for_borrower(self):
        self.client.force_login(self.borrower)

        response = self.client.get(
            reverse("listings:detail", kwargs={"pk": self.listing.pk})
        )

        self.assertContains(response, self.request_url)
        self.assertContains(response, "Request this item")

    def test_item_detail_does_not_offer_owner_a_request_button(self):
        self.client.force_login(self.lessor)

        response = self.client.get(
            reverse("listings:detail", kwargs={"pk": self.listing.pk})
        )

        self.assertNotContains(response, "Request this item")

    def test_borrower_can_submit_valid_request(self):
        self.client.force_login(self.borrower)

        response = self.client.post(
            self.request_url,
            self.valid_request_data(),
        )

        loan = Loan.objects.get()
        self.assertRedirects(
            response,
            reverse(
                "loans:request-confirmation",
                kwargs={"pk": loan.pk},
            ),
        )
        self.assertEqual(loan.listing, self.listing)
        self.assertEqual(loan.borrower, self.borrower)
        self.assertEqual(loan.status, LoanStatus.REQUESTED)
        self.assertEqual(
            loan.message,
            "Could I pick this up near the library?",
        )

    def test_coordination_message_is_optional(self):
        self.client.force_login(self.borrower)
        data = self.valid_request_data()
        data["message"] = ""

        response = self.client.post(self.request_url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Loan.objects.get().message, "")

    def test_owner_cannot_request_own_listing(self):
        self.client.force_login(self.lessor)

        response = self.client.get(self.request_url)

        self.assertRedirects(
            response,
            reverse("listings:detail", kwargs={"pk": self.listing.pk}),
        )
        self.assertFalse(Loan.objects.exists())

    def test_inactive_listing_cannot_be_requested(self):
        self.listing.is_active = False
        self.listing.save(update_fields=["is_active"])
        self.client.force_login(self.borrower)

        response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 404)

    def test_past_start_date_is_rejected(self):
        self.client.force_login(self.borrower)
        data = self.valid_request_data()
        data["start_date"] = (timezone.localdate() - timedelta(days=1)).isoformat()

        response = self.client.post(self.request_url, data)

        self.assertFormError(
            response.context["form"],
            "start_date",
            "The start date cannot be in the past.",
        )
        self.assertFalse(Loan.objects.exists())

    def test_start_date_after_return_date_is_rejected(self):
        self.client.force_login(self.borrower)
        data = self.valid_request_data()
        data["start_date"] = (
            self.listing.available_from + timedelta(days=3)
        ).isoformat()
        data["return_date"] = self.listing.available_from.isoformat()

        response = self.client.post(self.request_url, data)

        self.assertFormError(
            response.context["form"],
            "return_date",
            "The return date must be on or after the start date.",
        )
        self.assertFalse(Loan.objects.exists())

    def test_dates_before_listing_availability_are_rejected(self):
        self.client.force_login(self.borrower)
        data = self.valid_request_data()
        data["start_date"] = timezone.localdate().isoformat()

        response = self.client.post(self.request_url, data)

        self.assertFormError(
            response.context["form"],
            "start_date",
            "The start date must fall within the listing's availability.",
        )
        self.assertFalse(Loan.objects.exists())

    def test_dates_after_listing_availability_are_rejected(self):
        self.client.force_login(self.borrower)
        data = self.valid_request_data()
        data["return_date"] = (
            self.listing.available_until + timedelta(days=1)
        ).isoformat()

        response = self.client.post(self.request_url, data)

        self.assertFormError(
            response.context["form"],
            "return_date",
            "The return date must fall within the listing's availability.",
        )
        self.assertFalse(Loan.objects.exists())

    def test_request_exceeding_maximum_loan_length_is_rejected(self):
        self.client.force_login(self.borrower)
        data = self.valid_request_data()
        data["return_date"] = (
            self.listing.available_from + timedelta(days=4)
        ).isoformat()

        response = self.client.post(self.request_url, data)

        self.assertFormError(
            response.context["form"],
            "return_date",
            "The requested loan exceeds this item's maximum loan length.",
        )
        self.assertFalse(Loan.objects.exists())

    def test_pending_request_is_visible_to_listing_owner(self):
        loan = Loan.objects.create(
            listing=self.listing,
            borrower=self.borrower,
            start_date=self.listing.available_from,
            return_date=self.listing.available_from + timedelta(days=2),
            message="Please let me know.",
        )
        self.client.force_login(self.lessor)

        response = self.client.get(reverse("loans:pending-requests"))

        self.assertContains(response, loan.listing.title)
        self.assertContains(response, self.borrower.display_name)
        self.assertContains(response, "Please let me know.")

    def test_pending_request_is_not_visible_to_another_lessor(self):
        Loan.objects.create(
            listing=self.listing,
            borrower=self.borrower,
            start_date=self.listing.available_from,
            return_date=self.listing.available_from + timedelta(days=2),
        )
        self.client.force_login(self.other_lessor)

        response = self.client.get(reverse("loans:pending-requests"))

        self.assertNotContains(response, self.listing.title)

    def test_confirmation_page_is_limited_to_borrower(self):
        loan = Loan.objects.create(
            listing=self.listing,
            borrower=self.borrower,
            start_date=self.listing.available_from,
            return_date=self.listing.available_from + timedelta(days=2),
        )
        confirmation_url = reverse(
            "loans:request-confirmation",
            kwargs={"pk": loan.pk},
        )

        self.client.force_login(self.borrower)
        borrower_response = self.client.get(confirmation_url)
        self.assertEqual(borrower_response.status_code, 200)

        self.client.force_login(self.other_lessor)
        other_response = self.client.get(confirmation_url)
        self.assertEqual(other_response.status_code, 404)
