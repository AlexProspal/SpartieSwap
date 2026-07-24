from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .constants import CampusArea


class UserManager(BaseUserManager):
    # Django's default manager wants a username, so we need our own that takes
    # an email instead. createsuperuser goes through here too.

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    # Students log in with their school email, so we drop username entirely and
    # point USERNAME_FIELD at email. Setting a field to None removes it.
    # Doing this now because switching the user model after migrations exist is
    # a mess.
    username = None
    first_name = None
    last_name = None

    email = models.EmailField("university email", unique=True)
    display_name = models.CharField("name", max_length=80)
    campus_area = models.CharField(
        max_length=32,
        choices=CampusArea.choices,
        default=CampusArea.NORTH_RESIDENTIAL,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    objects = UserManager()

    def __str__(self):
        return self.display_name or self.email

    def get_short_name(self):
        return self.display_name or self.email

    def get_full_name(self):
        # AbstractUser builds this out of first_name/last_name, which we removed,
        # so override it or the admin blows up.
        return self.display_name or self.email
