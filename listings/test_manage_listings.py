from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.constants import CampusArea
from loans.models import Loan, LoanStatus

from .models import ItemCategory, ItemCondition, Listing


class ManageMyListingsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            email="lessor@case.edu",
            password="TestPassword123!",
            display_name="Test Lessor",
        )
        self.other_user = user_model.objects.create_user(
            email="other@case.edu",
            password="TestPassword123!",
            display_name="Other Student",
        )
        self.borrower = user_model.objects.create_user(
            email="borrower@case.edu",
            password="TestPassword123!",
            display_name="Test Borrower",
        )

        today = timezone.localdate()
        self.listing_data = {
            "description": "A useful item for local testing.",
            "category": ItemCategory.ELECTRONICS,
            "condition": ItemCondition.GOOD,
            "pickup_area": CampusArea.CASE_QUAD,
            "available_from": today + timedelta(days=1),
            "available_until": today + timedelta(days=10),
            "maximum_loan_days": 5,
        }

        self.active_listing = Listing.objects.create(
            owner=self.owner,
            title="Active Calculator",
            is_active=True,
            **self.listing_data,
        )
        self.inactive_listing = Listing.objects.create(
            owner=self.owner,
            title="Inactive Charger",
            is_active=False,
            **self.listing_data,
        )
        self.loaned_listing = Listing.objects.create(
            owner=self.owner,
            title="Loaned Drill",
            is_active=True,
            **self.listing_data,
        )
        Loan.objects.create(
            listing=self.loaned_listing,
            borrower=self.borrower,
            start_date=today + timedelta(days=2),
            return_date=today + timedelta(days=4),
            status=LoanStatus.PICKED_UP,
        )
        self.other_listing = Listing.objects.create(
            owner=self.other_user,
            title="Someone Else's Item",
            is_active=True,
            **self.listing_data,
        )

        self.client.force_login(self.owner)

    def valid_form_data(self, **overrides):
        data = {
            "title": "Updated Calculator",
            "description": "Updated description.",
            "category": ItemCategory.COURSE_MATERIALS,
            "condition": ItemCondition.LIKE_NEW,
            "pickup_area": CampusArea.UPTOWN,
            "available_from": (
                timezone.localdate() + timedelta(days=2)
            ).isoformat(),
            "available_until": (
                timezone.localdate() + timedelta(days=8)
            ).isoformat(),
            "maximum_loan_days": 4,
        }
        data.update(overrides)
        return data

    def test_my_listings_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("listings:my-listings"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_dashboard_separates_listing_states(self):
        response = self.client.get(reverse("listings:my-listings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Calculator")
        self.assertContains(response, "Inactive Charger")
        self.assertContains(response, "Loaned Drill")

        active = list(response.context["active_listings"])
        inactive = list(response.context["inactive_listings"])
        loaned = list(response.context["currently_loaned_listings"])

        self.assertEqual(active, [self.active_listing])
        self.assertEqual(inactive, [self.inactive_listing])
        self.assertEqual(loaned, [self.loaned_listing])

    def test_dashboard_excludes_another_users_listings(self):
        response = self.client.get(reverse("listings:my-listings"))

        self.assertNotContains(response, self.other_listing.title)

    def test_owner_can_edit_listing(self):
        response = self.client.post(
            reverse(
                "listings:edit",
                kwargs={"pk": self.active_listing.pk},
            ),
            self.valid_form_data(),
        )

        self.assertRedirects(response, reverse("listings:my-listings"))
        self.active_listing.refresh_from_db()
        self.assertEqual(self.active_listing.title, "Updated Calculator")
        self.assertEqual(
            self.active_listing.pickup_area,
            CampusArea.UPTOWN,
        )

    def test_listing_edit_is_visible_to_borrowers_immediately(self):
        self.client.post(
            reverse(
                "listings:edit",
                kwargs={"pk": self.active_listing.pk},
            ),
            self.valid_form_data(title="Updated Public Title"),
        )

        response = self.client.get(reverse("listings:list"))

        self.assertContains(response, "Updated Public Title")
        self.assertNotContains(response, "Active Calculator")

    def test_user_cannot_edit_another_users_listing(self):
        response = self.client.get(
            reverse(
                "listings:edit",
                kwargs={"pk": self.other_listing.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_can_deactivate_listing(self):
        response = self.client.post(
            reverse(
                "listings:deactivate",
                kwargs={"pk": self.active_listing.pk},
            )
        )

        self.assertRedirects(response, reverse("listings:my-listings"))
        self.active_listing.refresh_from_db()
        self.assertFalse(self.active_listing.is_active)

        browse_response = self.client.get(reverse("listings:list"))
        self.assertNotContains(
            browse_response,
            self.active_listing.title,
        )

    def test_owner_can_reactivate_listing(self):
        response = self.client.post(
            reverse(
                "listings:reactivate",
                kwargs={"pk": self.inactive_listing.pk},
            )
        )

        self.assertRedirects(response, reverse("listings:my-listings"))
        self.inactive_listing.refresh_from_db()
        self.assertTrue(self.inactive_listing.is_active)

        browse_response = self.client.get(reverse("listings:list"))
        self.assertContains(
            browse_response,
            self.inactive_listing.title,
        )

    def test_activation_changes_require_post(self):
        deactivate_response = self.client.get(
            reverse(
                "listings:deactivate",
                kwargs={"pk": self.active_listing.pk},
            )
        )
        reactivate_response = self.client.get(
            reverse(
                "listings:reactivate",
                kwargs={"pk": self.inactive_listing.pk},
            )
        )

        self.assertEqual(deactivate_response.status_code, 405)
        self.assertEqual(reactivate_response.status_code, 405)

    def test_user_cannot_change_another_users_listing_status(self):
        deactivate_response = self.client.post(
            reverse(
                "listings:deactivate",
                kwargs={"pk": self.other_listing.pk},
            )
        )
        reactivate_response = self.client.post(
            reverse(
                "listings:reactivate",
                kwargs={"pk": self.other_listing.pk},
            )
        )

        self.assertEqual(deactivate_response.status_code, 404)
        self.assertEqual(reactivate_response.status_code, 404)

    def test_owner_can_delete_listing_without_active_exchange(self):
        response = self.client.post(
            reverse(
                "listings:delete",
                kwargs={"pk": self.active_listing.pk},
            )
        )

        self.assertRedirects(response, reverse("listings:my-listings"))
        self.assertFalse(
            Listing.objects.filter(pk=self.active_listing.pk).exists()
        )

    def test_delete_get_displays_confirmation(self):
        response = self.client.get(
            reverse(
                "listings:delete",
                kwargs={"pk": self.active_listing.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_listing.title)
        self.assertTrue(
            Listing.objects.filter(pk=self.active_listing.pk).exists()
        )

    def test_delete_is_blocked_for_nonterminal_exchanges(self):
        today = timezone.localdate()
        blocking_statuses = [
            LoanStatus.REQUESTED,
            LoanStatus.APPROVED,
            LoanStatus.PICKED_UP,
            LoanStatus.RETURNED,
        ]

        for index, status in enumerate(blocking_statuses):
            with self.subTest(status=status):
                listing = Listing.objects.create(
                    owner=self.owner,
                    title=f"Blocked Listing {index}",
                    is_active=True,
                    **self.listing_data,
                )
                Loan.objects.create(
                    listing=listing,
                    borrower=self.borrower,
                    start_date=today + timedelta(days=2),
                    return_date=today + timedelta(days=4),
                    status=status,
                )

                response = self.client.post(
                    reverse(
                        "listings:delete",
                        kwargs={"pk": listing.pk},
                    )
                )

                self.assertRedirects(
                    response,
                    reverse("listings:my-listings"),
                )
                self.assertTrue(
                    Listing.objects.filter(pk=listing.pk).exists()
                )

    def test_terminal_exchange_does_not_block_deletion(self):
        today = timezone.localdate()
        listing = Listing.objects.create(
            owner=self.owner,
            title="Completed Exchange Listing",
            is_active=False,
            **self.listing_data,
        )
        Loan.objects.create(
            listing=listing,
            borrower=self.borrower,
            start_date=today - timedelta(days=4),
            return_date=today - timedelta(days=2),
            status=LoanStatus.COMPLETED,
        )

        response = self.client.post(
            reverse(
                "listings:delete",
                kwargs={"pk": listing.pk},
            )
        )

        self.assertRedirects(response, reverse("listings:my-listings"))
        self.assertFalse(Listing.objects.filter(pk=listing.pk).exists())

    def test_user_cannot_delete_another_users_listing(self):
        response = self.client.post(
            reverse(
                "listings:delete",
                kwargs={"pk": self.other_listing.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Listing.objects.filter(pk=self.other_listing.pk).exists()
        )
