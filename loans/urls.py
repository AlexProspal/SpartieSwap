from django.urls import path

from . import views

app_name = "loans"

urlpatterns = [
    path(
        "request/<int:listing_pk>/",
        views.request_listing,
        name="request-listing",
    ),
    path(
        "request/<int:pk>/submitted/",
        views.request_confirmation,
        name="request-confirmation",
    ),
    path(
        "requests/",
        views.pending_requests,
        name="pending-requests",
    ),
]
