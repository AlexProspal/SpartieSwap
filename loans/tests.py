from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.constants import CampusArea
from listings.models import ItemCategory, ItemCondition, Listing

from .models import LESSOR_TRANSITIONS, Loan, LoanStatus

User = get_user_model()


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
            return_date=date(2026, 7, 28),
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
        self.assertEqual(self.loan.status, LoanStatus.REQUESTED)

    def test_lessor_can_only_complete_a_returned_loan(self):
        with self.assertRaises(ValidationError):
            self.loan.transition_to(LoanStatus.COMPLETED, LESSOR_TRANSITIONS)

        self.loan.status = LoanStatus.RETURNED
        self.loan.save()
        self.loan.transition_to(LoanStatus.COMPLETED, LESSOR_TRANSITIONS)

        self.assertEqual(self.loan.status, LoanStatus.COMPLETED)


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
            return_date=date(2026, 7, 28),
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
            return_date=date(2026, 7, 28),
        )
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my-borrowing"))

        self.assertContains(response, self.listing.title)
        self.assertNotContains(response, other_listing.title)

    def test_pending_request_shows_only_cancel_action(self):
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my-borrowing"))

        self.assertContains(response, "Cancel request")
        self.assertNotContains(response, "Mark picked up")
        self.assertNotContains(response, "Mark returned")

    def test_approved_request_shows_only_pickup_action(self):
        self.loan.status = LoanStatus.APPROVED
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my-borrowing"))

        self.assertNotContains(response, "Cancel request")
        self.assertContains(response, "Mark picked up")
        self.assertNotContains(response, "Mark returned")

    def test_picked_up_request_shows_only_return_action(self):
        self.loan.status = LoanStatus.PICKED_UP
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my-borrowing"))

        self.assertNotContains(response, "Cancel request")
        self.assertNotContains(response, "Mark picked up")
        self.assertContains(response, "Mark returned")

    def test_completed_or_cancelled_request_shows_no_action(self):
        self.loan.status = LoanStatus.RETURNED
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my-borrowing"))

        self.assertNotContains(response, "Cancel request")
        self.assertNotContains(response, "Mark picked up")
        self.assertNotContains(response, "Mark returned")

    def test_borrower_can_cancel_pending_request(self):
        self.client.force_login(self.borrower)

        response = self.client.post(reverse("loans:cancel", kwargs={"pk": self.loan.pk}))

        self.assertRedirects(response, reverse("loans:my-borrowing"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.CANCELLED)

    def test_borrower_can_mark_approved_request_as_picked_up_then_returned(self):
        self.loan.status = LoanStatus.APPROVED
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.post(reverse("loans:pickup", kwargs={"pk": self.loan.pk}))

        self.assertRedirects(response, reverse("loans:my-borrowing"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.PICKED_UP)

        response = self.client.post(reverse("loans:return", kwargs={"pk": self.loan.pk}))

        self.assertRedirects(response, reverse("loans:my-borrowing"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.RETURNED)

    def test_invalid_view_transition_leaves_status_unchanged(self):
        self.client.force_login(self.borrower)

        response = self.client.post(reverse("loans:return", kwargs={"pk": self.loan.pk}))

        self.assertRedirects(response, reverse("loans:my-borrowing"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.REQUESTED)

    def test_other_user_cannot_update_request(self):
        self.client.force_login(self.other_borrower)

        response = self.client.post(reverse("loans:cancel", kwargs={"pk": self.loan.pk}))

        self.assertEqual(response.status_code, 404)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.REQUESTED)


class DeclinedAndCompletedDisplayTests(TestCase):
    """The statuses the borrowing dashboard needs from the request workflow.

    Declined and completed only exist because this branch moved onto the loan
    model from #22, so they are worth covering directly.
    """

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
            return_date=date(2026, 7, 28),
        )

    def test_declined_request_is_shown_as_closed_with_no_actions(self):
        self.loan.status = LoanStatus.DECLINED
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my-borrowing"))

        self.assertContains(response, "was declined and is closed")
        self.assertNotContains(response, "Cancel request")
        self.assertNotContains(response, "Mark picked up")
        self.assertNotContains(response, "Mark returned")

    def test_completed_loan_highlights_the_completed_step(self):
        self.loan.status = LoanStatus.COMPLETED
        self.loan.save()
        self.client.force_login(self.borrower)

        response = self.client.get(reverse("loans:my-borrowing"))

        self.assertContains(response, '<li class="fw-bold">Completed</li>', html=False)
        self.assertNotContains(response, '<li class="fw-bold">Returned</li>')

    def test_borrower_cannot_skip_from_requested_to_returned(self):
        with self.assertRaises(ValidationError):
            self.loan.transition_to(LoanStatus.RETURNED)

    def test_borrower_cannot_approve_their_own_request(self):
        # Approving belongs to the lessor, so it must not be reachable here.
        with self.assertRaises(ValidationError):
            self.loan.transition_to(LoanStatus.APPROVED)


class MyLendingViewTests(TestCase):
    def setUp(self):
        self.lessor = User.objects.create_user(
            email="lessor@case.edu",
            password="TestPassword123!",
            display_name="Test Lessor",
        )
        self.borrower = User.objects.create_user(
            email="borrower@case.edu",
            password="TestPassword123!",
            display_name="Test Borrower",
        )
        self.other_lessor = User.objects.create_user(
            email="other-lessor@case.edu",
            password="TestPassword123!",
            display_name="Other Lessor",
        )
        self.listing = self.create_listing(self.lessor, "TI-84 Calculator")
        self.loan = Loan.objects.create(
            listing=self.listing,
            borrower=self.borrower,
            start_date=date(2026, 7, 26),
            return_date=date(2026, 7, 28),
            status=LoanStatus.RETURNED,
        )

    def create_listing(self, owner, title):
        return Listing.objects.create(
            owner=owner,
            title=title,
            description="Available to borrow.",
            category=ItemCategory.ELECTRONICS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=date(2026, 7, 25),
            available_until=date(2026, 8, 1),
        )

    def test_dashboard_only_shows_current_users_active_lending_exchanges(self):
        other_listing = self.create_listing(self.other_lessor, "USB-C Charger")
        Loan.objects.create(
            listing=other_listing,
            borrower=self.borrower,
            start_date=date(2026, 7, 26),
            return_date=date(2026, 7, 28),
            status=LoanStatus.RETURNED,
        )
        completed_listing = self.create_listing(
            self.lessor,
            "Completed Calculator",
        )

        completed_loan = Loan.objects.create(
            listing=completed_listing,
            borrower=self.borrower,
            start_date=date(2026, 7, 26),
            return_date=date(2026, 7, 28),
            status=LoanStatus.COMPLETED,
        )
        self.client.force_login(self.lessor)

        response = self.client.get(reverse("loans:my-lending"))

        self.assertContains(response, self.listing.title)
        self.assertContains(response, self.borrower.display_name)
        self.assertContains(response, "Case Quad")
        self.assertNotContains(response, other_listing.title)
        self.assertNotContains(response, completed_listing.title)

    def test_confirm_return_button_only_appears_for_returned_loans(self):
        self.client.force_login(self.lessor)

        response = self.client.get(reverse("loans:my-lending"))
        self.assertContains(response, "Confirm return")

        self.loan.status = LoanStatus.PICKED_UP
        self.loan.save()
        response = self.client.get(reverse("loans:my-lending"))
        self.assertNotContains(response, "Confirm return")

    def test_owner_can_confirm_return(self):
        self.client.force_login(self.lessor)

        response = self.client.post(
            reverse("loans:confirm-return", kwargs={"pk": self.loan.pk})
        )

        self.assertRedirects(response, reverse("loans:my-lending"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.COMPLETED)

        response = self.client.get(reverse("loans:my-lending"))
        self.assertNotContains(response, "Confirm return")

    def test_non_owner_cannot_confirm_return(self):
        self.client.force_login(self.borrower)

        response = self.client.post(
            reverse("loans:confirm-return", kwargs={"pk": self.loan.pk})
        )

        self.assertEqual(response.status_code, 404)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.RETURNED)

    def test_invalid_confirm_return_transition_leaves_status_unchanged(self):
        self.loan.status = LoanStatus.PICKED_UP
        self.loan.save()
        self.client.force_login(self.lessor)

        response = self.client.post(
            reverse("loans:confirm-return", kwargs={"pk": self.loan.pk})
        )

        self.assertRedirects(response, reverse("loans:my-lending"))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, LoanStatus.PICKED_UP)
