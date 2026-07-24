from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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
    mine = Loan.objects.filter(listing__owner=request.user).select_related(
        "listing", "borrower"
    )

    # Completed loans stand in as reliability information until ratings arrive
    # with 2.3 and 2.4.
    pending = [
        (loan, _completed_loan_count(loan.borrower_id))
        for loan in mine.filter(status=LoanStatus.REQUESTED).order_by("-requested_at")
    ]
    approved = mine.filter(status=LoanStatus.APPROVED).order_by("start_date")

    return render(
        request,
        "loans/pending_requests.html",
        {"pending_requests": pending, "approved_loans": approved},
    )


def _completed_loan_count(borrower_id):
    return Loan.objects.filter(
        borrower_id=borrower_id, status=LoanStatus.COMPLETED
    ).count()


def _decide_request(request, pk, status):
    # Scoped to loans on the current user's own listings, so another lessor's
    # request is a 404 rather than a permission error.
    loan = get_object_or_404(
        Loan.objects.select_related("listing"),
        pk=pk,
        listing__owner=request.user,
    )
    try:
        loan.lessor_transition_to(status)
    except ValidationError as error:
        # Approval failures carry the clashing dates, so show what came back
        # rather than a generic message.
        messages.error(request, error.messages[0])
    else:
        messages.success(
            request,
            f'Request from {loan.borrower.get_short_name()} was '
            f"{loan.get_status_display().lower()}.",
        )
    return redirect("loans:pending-requests")


@login_required
@require_POST
def approve_request(request, pk):
    return _decide_request(request, pk, LoanStatus.APPROVED)


@login_required
@require_POST
def decline_request(request, pk):
    return _decide_request(request, pk, LoanStatus.DECLINED)


@login_required
@require_POST
def cancel_approved_loan(request, pk):
    return _decide_request(request, pk, LoanStatus.CANCELLED)


@login_required
def my_borrowing(request):
    loans = Loan.objects.filter(borrower=request.user).select_related(
        "listing", "listing__owner"
    )
    return render(request, "loans/my_borrowing.html", {"loans": loans})


def _advance_loan(request, pk, status):
    # Scoping the lookup to the logged-in borrower means someone else's loan is
    # a 404 rather than a permission error, which doesn't leak that it exists.
    loan = get_object_or_404(Loan, pk=pk, borrower=request.user)
    try:
        loan.borrower_transition_to(status)
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
