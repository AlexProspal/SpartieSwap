from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("", views.listing_list, name="list"),
    path("new/", views.listing_create, name="create"),
    path(
        "<int:pk>/owner/",
        views.listing_owner_controls,
        name="owner-controls",
    ),
    path("<int:pk>/", views.listing_detail, name="detail"),
]


# User Story 2.2: Manage My Listings
urlpatterns += [
    path("mine/", views.my_listings, name="my-listings"),
    path("<int:pk>/edit/", views.listing_edit, name="edit"),
    path(
        "<int:pk>/deactivate/",
        views.listing_deactivate,
        name="deactivate",
    ),
    path(
        "<int:pk>/reactivate/",
        views.listing_reactivate,
        name="reactivate",
    ),
    path("<int:pk>/delete/", views.listing_delete, name="delete"),
]
