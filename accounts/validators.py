from django.conf import settings
from django.core.exceptions import ValidationError


def validate_campus_email(value):
    """Blocks anyone whose email isn't at the school domain."""
    domain = settings.CAMPUS_EMAIL_DOMAIN.lower()

    # Split on the last @ and compare the whole domain. Checking with endswith
    # would let something like student@notcase.edu slip through.
    _, _, actual = value.rpartition("@")
    if actual.lower() != domain:
        raise ValidationError(
            "Enter a valid %(domain)s email address. SpartieSwap is limited to "
            "students with a university account.",
            params={"domain": domain},
            code="invalid_campus_email",
        )
