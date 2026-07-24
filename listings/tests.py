from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.constants import CampusArea

from .models import ItemCategory, ItemCondition, Listing


class ListingViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="borrower@case.edu",
            password="TestPassword123!",
            display_name="Test Borrower",
        )
        self.client.force_login(self.user)

        self.active_listing = Listing.objects.create(
            owner=self.user,
            title="TI-84 Calculator",
            description="A calculator available for exams.",
            category=ItemCategory.ELECTRONICS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=date(2026, 7, 25),
            available_until=date(2026, 8, 1),
            is_active=True,
        )

        self.inactive_listing = Listing.objects.create(
            owner=self.user,
            title="Inactive Textbook",
            description="This item should not appear.",
            category=ItemCategory.COURSE_MATERIALS,
            condition=ItemCondition.FAIR,
            pickup_area=CampusArea.NORTH_RESIDENTIAL,
            available_from=date(2026, 7, 25),
            available_until=date(2026, 8, 1),
            is_active=False,
        )

    def test_browse_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("listings:list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_browse_page_displays_active_listings(self):
        response = self.client.get(reverse("listings:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_listing.title)

    def test_browse_page_hides_inactive_listings(self):
        response = self.client.get(reverse("listings:list"))

        self.assertNotContains(response, self.inactive_listing.title)

    def test_browse_page_displays_required_information(self):
        response = self.client.get(reverse("listings:list"))

        self.assertContains(response, "Electronics")
        self.assertContains(response, "Good")
        self.assertContains(response, "Case Quad")
        self.assertContains(response, "July 25, 2026")
        self.assertContains(response, "Aug. 1, 2026")

    def test_listing_links_to_detail_page(self):
        response = self.client.get(reverse("listings:list"))
        detail_url = reverse(
            "listings:detail",
            kwargs={"pk": self.active_listing.pk},
        )

        self.assertContains(response, detail_url)

        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, self.active_listing.description)

    def test_inactive_listing_detail_returns_404(self):
        response = self.client.get(
            reverse(
                "listings:detail",
                kwargs={"pk": self.inactive_listing.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_new_active_listing_appears_without_restart(self):
        title = "USB-C Charger"
        response_before = self.client.get(reverse("listings:list"))
        self.assertNotContains(response_before, title)

        Listing.objects.create(
            owner=self.user,
            title=title,
            description="A spare laptop charger.",
            category=ItemCategory.ELECTRONICS,
            condition=ItemCondition.LIKE_NEW,
            pickup_area=CampusArea.UPTOWN,
            available_from=date(2026, 7, 26),
            available_until=date(2026, 8, 2),
        )

        response_after = self.client.get(reverse("listings:list"))
        self.assertContains(response_after, title)