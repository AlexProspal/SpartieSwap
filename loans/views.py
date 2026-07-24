from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from listings.models import Listing

from .forms import LoanRequestForm
from .models import LESSOR_TRANSITIONS, Loan, LoanStatus


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


@login_required
def my_borrowing(request):
    loans = Loan.objects.filter(borrower=request.user).select_related(
        "listing", "listing__owner"
    )
    return render(request, "loans/my_borrowing.html", {"loans": loans})


@login_required
def my_lending_view(request):
    loans = (
        Loan.objects.filter(
            listing__owner=request.user,
            status__in=[
                LoanStatus.APPROVED,
                LoanStatus.PICKED_UP,
                LoanStatus.RETURNED,
            ],
        )
        .select_related("listing", "borrower")
        .order_by("-requested_at")
    )
    return render(request, "loans/my_lending.html", {"loans": loans})


def _advance_loan(request, pk, status):
    # Scoping the lookup to the logged-in borrower means someone else's loan is
    # a 404 rather than a permission error, which doesn't leak that it exists.
    loan = get_object_or_404(Loan, pk=pk, borrower=request.user)
    try:
        loan.transition_to(status)
    except ValidationError:
        messages.error(request, "That action is not available for this borrowing request.")
    else:
        messages.success(request, f"Request marked as {loan.get_status_display()}.")
    return redirect("loans:my-borrowing")


@login_required
@require_POST
def cancel_request(request, pk):
    return _advance_loan(request, pk, LoanStatus.CANCELLED)


@login_required
@require_POST
def mark_picked_up(request, pk):
    return _advance_loan(request, pk, LoanStatus.PICKED_UP)


@login_required
@require_POST
def mark_returned(request, pk):
    return _advance_loan(request, pk, LoanStatus.RETURNED)


@login_required
@require_POST
def confirm_return_view(request, pk):
    loan = get_object_or_404(Loan, pk=pk, listing__owner=request.user)
    try:
        loan.transition_to(LoanStatus.COMPLETED, LESSOR_TRANSITIONS)
    except ValidationError:
        messages.error(request, "That action is not available for this lending exchange.")
    else:
        messages.success(request, f"Loan marked as {loan.get_status_display()}.")
    return redirect("loans:my-lending")
