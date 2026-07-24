from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .constants import CampusArea

User = get_user_model()


def signup_payload(**overrides):
    # Valid signup data. Pass a keyword to break one field at a time.
    payload = {
        "display_name": "Josef Broz",
        "email": "jxb1234@case.edu",
        "campus_area": CampusArea.NORTH_RESIDENTIAL,
        "password1": "swap-a-calculator-42",
        "password2": "swap-a-calculator-42",
    }
    payload.update(overrides)
    return payload


class HomePageTests(TestCase):
    def test_home_page_renders_for_anonymous_visitors(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")


class SignUpTests(TestCase):
    def test_campus_email_creates_account_and_signs_user_in(self):
        response = self.client.post(reverse("accounts:signup"), signup_payload())

        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(email="jxb1234@case.edu")
        self.assertEqual(user.display_name, "Josef Broz")
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_non_campus_email_is_rejected(self):
        response = self.client.post(
            reverse("accounts:signup"), signup_payload(email="jxb1234@gmail.com")
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "Enter a valid case.edu email address. SpartieSwap is limited to "
            "students with a university account.",
        )
        self.assertFalse(User.objects.exists())

    def test_lookalike_domain_is_rejected(self):
        # notcase.edu ends in case.edu, which is why the validator compares the
        # full domain instead of using endswith.
        response = self.client.post(
            reverse("accounts:signup"), signup_payload(email="jxb1234@notcase.edu")
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_email_is_normalized_to_lowercase(self):
        self.client.post(reverse("accounts:signup"), signup_payload(email="JXB1234@CASE.EDU"))

        self.assertTrue(User.objects.filter(email="jxb1234@case.edu").exists())

    def test_duplicate_email_is_rejected_regardless_of_case(self):
        self.client.post(reverse("accounts:signup"), signup_payload())

        response = self.client.post(
            reverse("accounts:signup"), signup_payload(email="JXB1234@case.edu")
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "email", "An account with this email already exists."
        )
        self.assertEqual(User.objects.count(), 1)

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            reverse("accounts:signup"), signup_payload(password2="something-else-entirely")
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())


class SessionTests(TestCase):
    def setUp(self):
        self.password = "swap-a-calculator-42"
        self.user = User.objects.create_user(
            email="gina@case.edu",
            password=self.password,
            display_name="Gina Cheng",
        )

    def test_login_with_email_succeeds(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.email, "password": self.password},
        )

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.email, "password": "not-the-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_ends_the_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)


class UserModelTests(TestCase):
    def test_create_user_requires_an_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x", display_name="No Email")

    def test_create_superuser_gets_staff_and_superuser_flags(self):
        admin = User.objects.create_superuser(
            email="admin@case.edu", password="x", display_name="Admin"
        )

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
