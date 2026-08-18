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
        "total_amount",
        "hold_expires_at",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_status",
        "booking_date",
        "venue",
    )

    search_fields = (
        "booking_id",
        "user__username",
        "user__email",
        "venue__venue_name",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "booking_id",
        "created_at",
        "updated_at",
    )