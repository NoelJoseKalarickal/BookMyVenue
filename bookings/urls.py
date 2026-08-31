from django.urls import path

from .views import (
    CreateBookingView,
    ConfirmBookingView,
    CancelBookingView,
    ProcessExpiredBookingsView,
    BookingDetailView,
    MyBookingsView,
)


urlpatterns = [

    path(
        "create/",
        CreateBookingView.as_view(),
        name="create-booking",
    ),

    path(
        "my/",
        MyBookingsView.as_view(),
        name="my-bookings",
    ),

    path(
        "<uuid:booking_id>/",
        BookingDetailView.as_view(),
        name="booking-detail",
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

    path(
        "process-expired/",
        ProcessExpiredBookingsView.as_view(),
        name="process-expired-bookings",
    ),
]