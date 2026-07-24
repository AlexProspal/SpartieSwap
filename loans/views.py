from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from listings.models import Listing

from .forms import LoanRequestForm
from .models import Loan, LoanStatus


@login_required
def request_listing(request, listing_pk):
    listing = get_object_or_404(
        Listing.objects.select_related("owner"),
        pk=listing_pk,
        is_active=True,
    )

    if listing.owner_id == request.user.id:
        messages.error(request, "You cannot request your own listing.")
        return redirect("listings:detail", pk=listing.pk)

    form = LoanRequestForm(
        request.POST or None,
        listing=listing,
        borrower=request.user,
    )

    if request.method == "POST" and form.is_valid():
        loan = form.save()
        messages.success(
            request,
            f'Your request for "{listing.title}" was submitted.',
        )
        return redirect("loans:request-confirmation", pk=loan.pk)

    return render(
        request,
        "loans/request_form.html",
        {
            "form": form,
            "listing": listing,
        },
    )


@login_required
def request_confirmation(request, pk):
    loan = get_object_or_404(
        Loan.objects.select_related("listing", "listing__owner"),
        pk=pk,
        borrower=request.user,
    )
    return render(
        request,
        "loans/request_confirmation.html",
        {"loan": loan},
    )


@login_required
def pending_requests(request):
    requests = (
        Loan.objects.filter(
            listing__owner=request.user,
            status=LoanStatus.REQUESTED,
        )
        .select_related("listing", "borrower")
        .order_by("-requested_at")
    )
    return render(
        request,
        "loans/pending_requests.html",
        {"loan_requests": requests},
    )
