from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Loan, LoanStatus


@login_required
def my_borrowing_view(request):
    loans = Loan.objects.filter(borrower=request.user).select_related("listing__owner")
    return render(request, "loans/my_borrowing.html", {"loans": loans})


def _transition_loan(request, pk, status):
    loan = get_object_or_404(Loan, pk=pk, borrower=request.user)
    try:
        loan.transition_to(status)
    except ValidationError:
        messages.error(request, "That action is not available for this borrowing request.")
    else:
        messages.success(request, f"Request marked as {loan.get_status_display()}.")
    return redirect("loans:my_borrowing")


@login_required
@require_POST
def cancel_request_view(request, pk):
    return _transition_loan(request, pk, LoanStatus.CANCELLED)


@login_required
@require_POST
def mark_picked_up_view(request, pk):
    return _transition_loan(request, pk, LoanStatus.PICKED_UP)


@login_required
@require_POST
def mark_returned_view(request, pk):
    return _transition_loan(request, pk, LoanStatus.RETURNED)
