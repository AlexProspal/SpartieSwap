from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

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