from django.urls import path

from . import views

app_name = "loans"

urlpatterns = [
    path("", views.my_borrowing_view, name="my_borrowing"),
    path("<int:pk>/cancel/", views.cancel_request_view, name="cancel"),
    path("<int:pk>/pickup/", views.mark_picked_up_view, name="pickup"),
    path("<int:pk>/return/", views.mark_returned_view, name="return"),
]
