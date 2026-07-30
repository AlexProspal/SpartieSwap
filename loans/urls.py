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
    path(
        "requests/<int:pk>/approve/",
        views.approve_request,
        name="approve",
    ),
    path(
        "requests/<int:pk>/decline/",
        views.decline_request,
        name="decline",
    ),
    path(
        "requests/<int:pk>/cancel/",
        views.cancel_approved_loan,
        name="cancel-approved",
    ),
    path(
        "borrowing/",
        views.my_borrowing,
        name="my-borrowing",
    ),
    path(
        "lending/",
        views.my_lending_view,
        name="my-lending",
    ),
    path(
        "borrowing/<int:pk>/cancel/",
        views.cancel_request,
        name="cancel",
    ),
    path(
        "borrowing/<int:pk>/pickup/",
        views.mark_picked_up,
        name="pickup",
    ),
    path(
        "borrowing/<int:pk>/return/",
        views.mark_returned,
        name="return",
    ),
    path(
        "borrowing/<int:pk>/review-lessor/",
        views.review_lessor,
        name="review-lessor",
    ),
    path(
        "lending/<int:pk>/confirm-return/",
        views.confirm_return_view,
        name="confirm-return",
    ),
    path(
        "lending/<int:pk>/review-borrower/",
        views.review_borrower,
        name="review-borrower",
    ),
]
