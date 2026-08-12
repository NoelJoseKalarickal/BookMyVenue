from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):

    list_display = (
        "booking_id",
        "user",
        "venue",
        "booking_date",
        "start_time",
        "end_time",
        "status",
        "queue_position",
        "payment_status",
        "hold_expires_at",
    )

    search_fields = (
        "booking_id",
        "user__username",
        "venue__venue_name",
    )

    list_filter = (
        "status",
        "payment_status",
        "booking_date",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "booking_id",
        "created_at",
        "updated_at",
    )