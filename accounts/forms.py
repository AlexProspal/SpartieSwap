from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User
from .validators import validate_campus_email


class SignUpForm(UserCreationForm):
    # Same fields as the signup card in Figure 1. The two password boxes come
    # from UserCreationForm, we don't have to list them.

    class Meta:
        model = User
        fields = ["display_name", "email", "campus_area"]
        labels = {
            "display_name": "Name",
            "email": "University email",
            "campus_area": "General campus area",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        # Lowercase everything first so the same address always looks the same
        # in the database.
        email = self.cleaned_data["email"].strip().lower()
        validate_campus_email(email)

        # unique=True on the model is case sensitive, so Jo@case.edu and
        # jo@case.edu would both get through. Check it ourselves.
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(AuthenticationForm):
    # Django's login form calls this field "username" internally and renaming it
    # breaks the view, so just relabel it for the page.
    username = forms.EmailField(label="University email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
