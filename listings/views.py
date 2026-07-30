from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from loans.models import Loan, LoanStatus

from .forms import ListingFilterForm, ListingForm
from .models import Listing


@login_required
def listing_list(request):
    # `or None` keeps the form unbound on a plain visit, so arriving at the page
    # normally doesn't show validation errors for fields nobody has filled in.
    form = ListingFilterForm(request.GET or None)
    listings = form.apply(Listing.objects.filter(is_active=True).select_related("owner"))
    return render(
        request,
        "listings/listing_list.html",
        {
            "listings": listings,
            "form": form,
            "is_filtered": form.is_filtered,
        },
    )


@login_required
def listing_detail(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related("owner"),
        pk=pk,
        is_active=True,
    )
    return render(
        request,
        "listings/listing_detail.html",
        {"listing": listing},
    )


@login_required
def listing_create(request):
    form = ListingForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        listing = form.save(commit=False)
        listing.owner = request.user
        listing.save()
        messages.success(request, f'"{listing.title}" was published successfully.')
        return redirect("listings:list")

    return render(
        request,
        "listings/listing_form.html",
        {"form": form},
    )


@login_required
def listing_owner_controls(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related("owner"),
        pk=pk,
        owner=request.user,
    )
    return render(
        request,
        "listings/listing_owner_controls.html",
        {"listing": listing},
    )


# ---------------------------------------------------------------------------
# User Story 2.2: Manage My Listings
# ---------------------------------------------------------------------------


ACTIVE_EXCHANGE_STATUSES = {
    LoanStatus.REQUESTED,
    LoanStatus.APPROVED,
    LoanStatus.PICKED_UP,
    LoanStatus.RETURNED,
}

CURRENTLY_LOANED_STATUSES = {
    LoanStatus.APPROVED,
    LoanStatus.PICKED_UP,
    LoanStatus.RETURNED,
}


@login_required
def my_listings(request):
    active_exchange = Loan.objects.filter(
        listing=OuterRef("pk"),
        status__in=ACTIVE_EXCHANGE_STATUSES,
    )
    currently_loaned = Loan.objects.filter(
        listing=OuterRef("pk"),
        status__in=CURRENTLY_LOANED_STATUSES,
    )

    listings = (
        Listing.objects.filter(owner=request.user)
        .annotate(
            has_active_exchange=Exists(active_exchange),
            is_currently_loaned=Exists(currently_loaned),
        )
        .order_by("-created_at")
    )

    context = {
        "active_listings": [
            listing
            for listing in listings
            if listing.is_active and not listing.is_currently_loaned
        ],
        "inactive_listings": [
            listing
            for listing in listings
            if not listing.is_active and not listing.is_currently_loaned
        ],
        "currently_loaned_listings": [
            listing for listing in listings if listing.is_currently_loaned
        ],
    }
    return render(request, "listings/my_listings.html", context)


@login_required
def listing_edit(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk,
        owner=request.user,
    )
    form = ListingForm(
        request.POST or None,
        request.FILES or None,
        instance=listing,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            f'"{listing.title}" was updated successfully.',
        )
        return redirect("listings:my-listings")

    return render(
        request,
        "listings/listing_edit.html",
        {
            "form": form,
            "listing": listing,
        },
    )


@login_required
@require_POST
def listing_deactivate(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk,
        owner=request.user,
    )

    if listing.is_active:
        listing.is_active = False
        listing.save(update_fields=["is_active", "updated_at"])
        messages.success(
            request,
            f'"{listing.title}" was deactivated.',
        )
    else:
        messages.info(
            request,
            f'"{listing.title}" is already inactive.',
        )

    return redirect("listings:my-listings")


@login_required
@require_POST
def listing_reactivate(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk,
        owner=request.user,
    )

    if not listing.is_active:
        listing.is_active = True
        listing.save(update_fields=["is_active", "updated_at"])
        messages.success(
            request,
            f'"{listing.title}" was reactivated.',
        )
    else:
        messages.info(
            request,
            f'"{listing.title}" is already active.',
        )

    return redirect("listings:my-listings")


@login_required
def listing_delete(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk,
        owner=request.user,
    )
    has_active_exchange = listing.loan_requests.filter(
        status__in=ACTIVE_EXCHANGE_STATUSES,
    ).exists()

    if has_active_exchange:
        messages.error(
            request,
            (
                f'"{listing.title}" cannot be deleted while it has a pending '
                "request or active exchange."
            ),
        )
        return redirect("listings:my-listings")

    if request.method == "POST":
        title = listing.title
        listing.delete()
        messages.success(
            request,
            f'"{title}" was deleted.',
        )
        return redirect("listings:my-listings")

    return render(
        request,
        "listings/listing_confirm_delete.html",
        {"listing": listing},
    )
