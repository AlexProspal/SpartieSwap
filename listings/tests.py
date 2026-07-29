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


class ListingCreationTests(TestCase):
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
        self.valid_data = {
            "title": "Cordless Drill",
            "description": "A working drill with a charged battery.",
            "category": ItemCategory.TOOLS,
            "condition": ItemCondition.GOOD,
            "pickup_area": CampusArea.CASE_QUAD,
            "available_from": "2026-07-25",
            "available_until": "2026-08-01",
            "maximum_loan_days": 3,
        }

    def test_create_listing_requires_login(self):
        response = self.client.get(reverse("listings:create"))

        expected_url = (
            f"{reverse('accounts:login')}?next={reverse('listings:create')}"
        )
        self.assertRedirects(response, expected_url)

    def test_owner_can_publish_valid_listing(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("listings:create"),
            self.valid_data,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        listing = Listing.objects.get(title="Cordless Drill")
        self.assertEqual(listing.owner, self.owner)
        self.assertContains(response, "Cordless Drill")

    def test_image_is_optional(self):
        self.client.force_login(self.owner)

        self.client.post(reverse("listings:create"), self.valid_data)

        listing = Listing.objects.get(title="Cordless Drill")
        self.assertFalse(listing.image)

    def test_missing_required_information_shows_clear_error(self):
        self.client.force_login(self.owner)
        invalid_data = self.valid_data.copy()
        invalid_data["title"] = ""

        response = self.client.post(reverse("listings:create"), invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "title",
            "This field is required.",
        )
        self.assertFalse(Listing.objects.exists())

    def test_invalid_availability_range_shows_clear_error(self):
        self.client.force_login(self.owner)
        invalid_data = self.valid_data.copy()
        invalid_data["available_from"] = "2026-08-01"
        invalid_data["available_until"] = "2026-07-25"

        response = self.client.post(reverse("listings:create"), invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "available_until",
            "The availability end date must be on or after the start date.",
        )
        self.assertFalse(Listing.objects.exists())

    def test_maximum_loan_length_cannot_exceed_availability(self):
        self.client.force_login(self.owner)
        invalid_data = self.valid_data.copy()
        invalid_data["maximum_loan_days"] = 20

        response = self.client.post(reverse("listings:create"), invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "maximum_loan_days",
            (
                "The maximum loan length cannot exceed the listing's "
                "availability period."
            ),
        )
        self.assertFalse(Listing.objects.exists())

    def test_only_owner_can_access_owner_controls(self):
        listing = Listing.objects.create(
            owner=self.owner,
            title="Calculator",
            description="A calculator.",
            category=ItemCategory.COURSE_MATERIALS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=date(2026, 7, 25),
            available_until=date(2026, 8, 1),
            maximum_loan_days=3,
        )
        owner_url = reverse(
            "listings:owner-controls",
            kwargs={"pk": listing.pk},
        )

        self.client.force_login(self.owner)
        owner_response = self.client.get(owner_url)

        self.assertEqual(owner_response.status_code, 200)
        self.assertContains(owner_response, "Owner controls")

        self.client.force_login(self.other_user)
        other_response = self.client.get(owner_url)

        self.assertEqual(other_response.status_code, 404)


class SearchAndFilterTests(TestCase):
    """Story 2.1 - keyword search and combined filters on the browse page."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="searcher@case.edu",
            password="TestPassword123!",
            display_name="Test Borrower",
        )
        self.client.force_login(self.user)
        self.url = reverse("listings:list")

        self.drill = self.make(
            title="Cordless Drill",
            description="Ryobi 18V with a full bit set.",
            category=ItemCategory.TOOLS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=date(2026, 8, 1),
            available_until=date(2026, 8, 20),
        )
        self.calculator = self.make(
            title="TI-84 Plus CE",
            description="Graphing calculator, good for exams.",
            category=ItemCategory.COURSE_MATERIALS,
            condition=ItemCondition.LIKE_NEW,
            pickup_area=CampusArea.NORTH_RESIDENTIAL,
            available_from=date(2026, 8, 10),
            available_until=date(2026, 8, 31),
        )
        self.tent = self.make(
            title="Camping Tent",
            description="Two person, sets up fast. Comes with a drill-free peg set.",
            category=ItemCategory.RECREATION,
            condition=ItemCondition.FAIR,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=date(2026, 9, 1),
            available_until=date(2026, 9, 30),
        )
        self.hidden = self.make(
            title="Retired Drill",
            description="Deactivated drill that must never show up.",
            category=ItemCategory.TOOLS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from=date(2026, 8, 1),
            available_until=date(2026, 8, 20),
            is_active=False,
        )

    def make(self, **fields):
        fields.setdefault("owner", self.user)
        fields.setdefault("maximum_loan_days", 7)
        return Listing.objects.create(**fields)

    def results(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return response, list(response.context["listings"])

    # --- keyword search ---

    def test_no_filters_shows_every_active_listing(self):
        _, found = self.results()

        self.assertCountEqual(found, [self.drill, self.calculator, self.tent])

    def test_search_matches_the_title(self):
        _, found = self.results(q="Cordless")

        self.assertEqual(found, [self.drill])

    def test_search_matches_the_description(self):
        _, found = self.results(q="Graphing")

        self.assertEqual(found, [self.calculator])

    def test_search_ignores_case(self):
        _, found = self.results(q="cordless drill")

        self.assertEqual(found, [self.drill])

    def test_search_matches_a_partial_word(self):
        _, found = self.results(q="calc")

        self.assertEqual(found, [self.calculator])

    def test_search_spanning_title_and_description_returns_both(self):
        # "drill" is in the drill's title and in the tent's description.
        _, found = self.results(q="drill")

        self.assertCountEqual(found, [self.drill, self.tent])

    def test_surrounding_whitespace_is_ignored(self):
        _, found = self.results(q="   Cordless   ")

        self.assertEqual(found, [self.drill])

    def test_whitespace_only_search_is_treated_as_empty(self):
        _, found = self.results(q="   ")

        self.assertCountEqual(found, [self.drill, self.calculator, self.tent])

    def test_search_never_returns_inactive_listings(self):
        _, found = self.results(q="Drill")

        self.assertNotIn(self.hidden, found)

    # --- individual filters ---

    def test_filter_by_category(self):
        _, found = self.results(category=ItemCategory.TOOLS)

        self.assertEqual(found, [self.drill])

    def test_filter_by_condition(self):
        _, found = self.results(condition=ItemCondition.FAIR)

        self.assertEqual(found, [self.tent])

    def test_filter_by_pickup_area(self):
        _, found = self.results(pickup_area=CampusArea.CASE_QUAD)

        self.assertCountEqual(found, [self.drill, self.tent])

    def test_filter_by_needed_from_date(self):
        # Only the drill's window covers 5 August.
        _, found = self.results(available_from="2026-08-05")

        self.assertEqual(found, [self.drill])

    def test_filter_by_needed_until_date(self):
        # Only the tent's window covers 15 September.
        _, found = self.results(available_until="2026-09-15")

        self.assertEqual(found, [self.tent])

    def test_date_range_needs_the_whole_span_available(self):
        # 12-18 August sits inside both the drill and the calculator windows.
        _, found = self.results(
            available_from="2026-08-12", available_until="2026-08-18"
        )

        self.assertCountEqual(found, [self.drill, self.calculator])

    def test_range_extending_past_a_window_drops_that_listing(self):
        # 18-25 August. The drill covers the 18th but is gone by the 20th, so it
        # can't cover the whole range; the calculator runs to the 31st and can.
        _, found = self.results(
            available_from="2026-08-18", available_until="2026-08-25"
        )

        self.assertEqual(found, [self.calculator])

    def test_availability_boundary_dates_are_inclusive(self):
        _, found = self.results(available_from="2026-08-01")

        self.assertIn(self.drill, found)

    # --- combined filters ---

    def test_two_filters_narrow_further_than_one(self):
        _, only_area = self.results(pickup_area=CampusArea.CASE_QUAD)
        _, area_and_category = self.results(
            pickup_area=CampusArea.CASE_QUAD, category=ItemCategory.TOOLS
        )

        self.assertCountEqual(only_area, [self.drill, self.tent])
        self.assertEqual(area_and_category, [self.drill])

    def test_search_combined_with_filters(self):
        _, found = self.results(
            q="drill",
            pickup_area=CampusArea.CASE_QUAD,
            category=ItemCategory.RECREATION,
        )

        self.assertEqual(found, [self.tent])

    def test_all_filters_at_once(self):
        _, found = self.results(
            q="Ryobi",
            category=ItemCategory.TOOLS,
            condition=ItemCondition.GOOD,
            pickup_area=CampusArea.CASE_QUAD,
            available_from="2026-08-02",
            available_until="2026-08-09",
        )

        self.assertEqual(found, [self.drill])

    def test_contradictory_filters_return_nothing(self):
        _, found = self.results(
            category=ItemCategory.TOOLS, condition=ItemCondition.FAIR
        )

        self.assertEqual(found, [])

    # --- empty state and messaging ---

    def test_empty_result_explains_that_nothing_matched(self):
        response, found = self.results(q="unicycle")

        self.assertEqual(found, [])
        self.assertContains(response, "No items match your search")

    def test_empty_result_offers_a_way_to_clear_the_filters(self):
        response, _ = self.results(q="unicycle")

        self.assertContains(response, "Clear filters")

    def test_unfiltered_empty_page_uses_the_other_message(self):
        Listing.objects.all().delete()

        response, found = self.results()

        self.assertEqual(found, [])
        self.assertContains(response, "No active listings are currently available")
        self.assertNotContains(response, "No items match your search")

    def test_match_count_is_shown_when_filtering(self):
        response, _ = self.results(pickup_area=CampusArea.CASE_QUAD)

        self.assertContains(response, "2 items matched")

    def test_count_is_not_shown_on_an_unfiltered_page(self):
        response, _ = self.results()

        self.assertNotContains(response, "items matched")

    # --- form behaviour ---

    def test_filters_are_kept_in_the_form_after_searching(self):
        response, _ = self.results(q="Cordless", category=ItemCategory.TOOLS)

        form = response.context["form"]
        self.assertEqual(form["q"].value(), "Cordless")
        self.assertEqual(form["category"].value(), ItemCategory.TOOLS)

    def test_arriving_without_filters_shows_no_validation_errors(self):
        response, _ = self.results()

        self.assertFalse(response.context["form"].is_bound)
        self.assertEqual(response.context["form"].errors, {})

    def test_reversed_date_range_is_rejected(self):
        response, _ = self.results(
            available_from="2026-08-20", available_until="2026-08-01"
        )

        self.assertIn("available_until", response.context["form"].errors)

    def test_reversed_date_range_still_lists_the_active_items(self):
        # Better to show everything with the error attached than an empty page
        # that looks like nothing exists.
        response, found = self.results(
            available_from="2026-08-20", available_until="2026-08-01"
        )

        self.assertCountEqual(found, [self.drill, self.calculator, self.tent])
        self.assertContains(response, "filters were not valid")

    def test_unparseable_date_is_rejected_without_a_crash(self):
        response, found = self.results(available_from="not-a-date")

        self.assertIn("available_from", response.context["form"].errors)
        self.assertCountEqual(found, [self.drill, self.calculator, self.tent])

    def test_unknown_category_value_is_rejected(self):
        response, found = self.results(category="not-a-real-category")

        self.assertIn("category", response.context["form"].errors)
        self.assertCountEqual(found, [self.drill, self.calculator, self.tent])

    def test_search_page_still_requires_login(self):
        self.client.logout()

        response = self.client.get(self.url, {"q": "drill"})

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_zero_match_page_does_not_also_print_a_count(self):
        # The empty state already explains it; "0 items matched" on top reads badly.
        response, found = self.results(q="unicycle")

        self.assertEqual(found, [])
        self.assertNotContains(response, "0 items matched")
