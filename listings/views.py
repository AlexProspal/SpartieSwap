from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ListingForm
from .models import Listing


@login_required
def listing_list(request):
    listings = Listing.objects.filter(is_active=True).select_related("owner")
    return render(
        request,
        "listings/listing_list.html",
        {"listings": listings},
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
