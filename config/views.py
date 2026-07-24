from django.shortcuts import render

from accounts.forms import SignUpForm


def home(request):
    # Landing page from Figure 1 - explanation on the left, signup box on the
    # right. The form posts over to the accounts app to actually create the user.
    return render(request, "home.html", {"form": SignUpForm()})
