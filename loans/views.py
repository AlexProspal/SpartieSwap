from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from listings.models import Listing

from .forms import LoanRequestForm, ReviewForm
from .models import Loan, LoanStatus, Review


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
    loans = (
        Loan.objects.filter(borrower=request.user)
        .select_related("listing", "listing__owner")
        .order_by("-requested_at")
    )

    active_statuses = [
        LoanStatus.REQUESTED,
        LoanStatus.APPROVED,
        LoanStatus.PICKED_UP,
        LoanStatus.RETURNED,
    ]

    previous_statuses = [
        LoanStatus.COMPLETED,
        LoanStatus.DECLINED,
        LoanStatus.CANCELLED,
    ]

    active_loans = list(loans.filter(status__in=active_statuses))
    previous_loans = list(loans.filter(status__in=previous_statuses))
    all_loans = active_loans + previous_loans

    owner_ids = {loan.listing.owner_id for loan in all_loans}
    reviewed_loan_ids = set(
        Review.objects.filter(
            reviewer=request.user,
            loan_id__in=[loan.pk for loan in previous_loans],
        ).values_list("loan_id", flat=True)
    )
    lessor_ratings = {
        row["reviewee_id"]: row["average_rating"]
        for row in Review.objects.filter(
            reviewee_id__in=owner_ids,
            reviewee_id=F("loan__listing__owner_id"),
        )
        .values("reviewee_id")
        .annotate(average_rating=Avg("rating"))
    }
    completed_loan_counts = {
        row["listing__owner_id"]: row["completed_count"]
        for row in Loan.objects.filter(
            listing__owner_id__in=owner_ids,
            status=LoanStatus.COMPLETED,
        )
        .values("listing__owner_id")
        .annotate(completed_count=Count("id"))
    }

    for loan in all_loans:
        owner_id = loan.listing.owner_id
        loan.borrower_has_reviewed = loan.pk in reviewed_loan_ids
        loan.lessor_average_rating = lessor_ratings.get(owner_id)
        loan.lessor_completed_loan_count = completed_loan_counts.get(owner_id, 0)

    return render(
        request,
        "loans/my_borrowing.html",
        {
            "active_loans": active_loans,
            "previous_loans": previous_loans,
        },
    )


@login_required
def review_lessor(request, pk):
    loan = get_object_or_404(
        Loan.objects.select_related("listing", "listing__owner"),
        pk=pk,
        borrower=request.user,
        status=LoanStatus.COMPLETED,
    )

    if Review.objects.filter(loan=loan, reviewer=request.user).exists():
        messages.info(request, "You have already reviewed the lessor for this loan.")
        return redirect("loans:my-borrowing")

    form = ReviewForm(
        request.POST or None,
        loan=loan,
        reviewer=request.user,
        reviewee=loan.listing.owner,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your review of the lessor was submitted.")
        return redirect("loans:my-borrowing")

    return render(
        request,
        "loans/review_lessor_form.html",
        {
            "form": form,
            "loan": loan,
        },
    )


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


@login_required
@require_POST
def confirm_return_view(request, pk):
    loan = get_object_or_404(Loan, pk=pk, listing__owner=request.user)
    try:
        loan.lessor_transition_to(LoanStatus.COMPLETED)
    except ValidationError:
        messages.error(request, "That action is not available for this lending exchange.")
    else:
        messages.success(request, f"Loan marked as {loan.get_status_display()}.")
    return redirect("loans:my-lending")
