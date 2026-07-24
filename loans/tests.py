from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.constants import CampusArea
from listings.models import ItemCategory, ItemCondition, Listing

from .models import Loan, LoanStatus

User = get_user_model()


class LoanModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@case.edu",
            password="TestPassword123!",
            display_name="Listing Owner",
        )
        self.borrower = User.objects.create_user(
            email="borrower@case.edu",
            password="TestPassword123!",
            display_name="Test Borrower",
        )
        self.listing = Listing.objects.create(
            owner=self.owner,
            title="TI-84 Calculator",
            description="A calculator for exams.",
            category=ItemCategory.ELECTRONICS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=date(2026, 7, 25),
            available_until=date(2026, 8, 1),
        )
        self.loan = Loan.objects.create(
            listing=self.listing,
            borrower=self.borrower,
            start_date=date(2026, 7, 26),
            end_date=date(2026, 7, 28),
        )

    def test_valid_status_progression(self):
        self.loan.status = LoanStatus.APPROVED
        self.loan.save()

        self.loan.transition_to(LoanStatus.PICKED_UP)
        self.loan.transition_to(LoanStatus.RETURNED)

        self.assertEqual(self.loan.status, LoanStatus.RETURNED)

    def test_pending_request_can_be_cancelled(self):
        self.loan.transition_to(LoanStatus.CANCELLED)

        self.assertEqual(self.loan.status, LoanStatus.CANCELLED)

    def test_invalid_status_transition_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.loan.transition_to(LoanStatus.RETURNED)

        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.PENDING)


class MyBorrowingViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@case.edu",
            password="TestPassword123!",
            display_name="Listing Owner",
        )
        self.borrower = User.objects.create_user(
            email="borrower@case.edu",
            password="TestPassword123!",
            display_name="Test Borrower",
        )
        self.other_borrower = User.objects.create_user(
            email="other@case.edu",
            password="TestPassword123!",
            display_name="Other Borrower",
        )
        self.listing = Listing.objects.create(
            owner=self.owner,
            title="TI-84 Calculator",
            description="A calculator for exams.",
            category=ItemCategory.ELECTRONICS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=date(2026, 7, 25),
            available_until=date(2026, 8, 1),
        )
        self.loan = Loan.objects.create(
            listing=self.listing,
            borrower=self.borrower,
            start_date=date(2026, 7, 26),
            end_date=date(2026, 7, 28),
        )

    def test_dashboard_only_shows_current_users_requests(self):
        other_listing = Listing.objects.create(
            owner=self.owner,
            title="USB-C Charger",
            description="A spare charger.",
            category=ItemCategory.ELECTRONICS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=date(2026, 7, 25),
            available_until=date(2026, 8, 1),
        )
        Loan.objects.create(
            listing=other_listing,
            borrower=self.other_borrower,
            start_date=date(2026, 7, 26),
            end_date=date(2026, 7, 28),
        )
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my_borrowing"))

        self.assertContains(response, self.listing.title)
        self.assertNotContains(response, other_listing.title)

    def test_pending_request_shows_only_cancel_action(self):
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my_borrowing"))

        self.assertContains(response, "Cancel request")
        self.assertNotContains(response, "Mark picked up")
        self.assertNotContains(response, "Mark returned")

    def test_approved_request_shows_only_pickup_action(self):
        self.loan.status = LoanStatus.APPROVED
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my_borrowing"))

        self.assertNotContains(response, "Cancel request")
        self.assertContains(response, "Mark picked up")
        self.assertNotContains(response, "Mark returned")

    def test_picked_up_request_shows_only_return_action(self):
        self.loan.status = LoanStatus.PICKED_UP
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my_borrowing"))

        self.assertNotContains(response, "Cancel request")
        self.assertNotContains(response, "Mark picked up")
        self.assertContains(response, "Mark returned")

    def test_completed_or_cancelled_request_shows_no_action(self):
        self.loan.status = LoanStatus.RETURNED
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my_borrowing"))

        self.assertNotContains(response, "Cancel request")
        self.assertNotContains(response, "Mark picked up")
        self.assertNotContains(response, "Mark returned")

    def test_borrower_can_cancel_pending_request(self):
        self.client.force_login(self.borrower)

        response = self.client.post(reverse("loans:cancel", kwargs={"pk": self.loan.pk}))

        self.assertRedirects(response, reverse("loans:my_borrowing"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.CANCELLED)

    def test_borrower_can_mark_approved_request_as_picked_up_then_returned(self):
        self.loan.status = LoanStatus.APPROVED
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.post(reverse("loans:pickup", kwargs={"pk": self.loan.pk}))

        self.assertRedirects(response, reverse("loans:my_borrowing"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.PICKED_UP)

        response = self.client.post(reverse("loans:return", kwargs={"pk": self.loan.pk}))

        self.assertRedirects(response, reverse("loans:my_borrowing"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.RETURNED)

    def test_invalid_view_transition_leaves_status_unchanged(self):
        self.client.force_login(self.borrower)

        response = self.client.post(reverse("loans:return", kwargs={"pk": self.loan.pk}))

        self.assertRedirects(response, reverse("loans:my_borrowing"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.PENDING)

    def test_other_user_cannot_update_request(self):
        self.client.force_login(self.other_borrower)

        response = self.client.post(reverse("loans:cancel", kwargs={"pk": self.loan.pk}))

        self.assertEqual(response.status_code, 404)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.PENDING)
