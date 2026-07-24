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
