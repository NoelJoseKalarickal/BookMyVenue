from django.urls import path

from .views import (
    CreateBookingView,
    ConfirmBookingView,
    CancelBookingView,
)


urlpatterns = [

    path(
        "create/",
        CreateBookingView.as_view(),
        name="create-booking",
    ),

    path(
        "<uuid:booking_id>/confirm/",
        ConfirmBookingView.as_view(),
        name="confirm-booking",
    ),

    path(
        "<uuid:booking_id>/cancel/",
        CancelBookingView.as_view(),
        name="cancel-booking",
    ),

]