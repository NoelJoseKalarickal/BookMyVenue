import nested_admin

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    EventType,
    Venue,
    VenueImage,
    WeeklySchedule,
    WeeklyTimeSlot,
    AvailabilityOverride,
)


class VenueImageInline(nested_admin.NestedTabularInline):
    model = VenueImage
    extra = 1

    fields = (
        "preview",
        "image",
        "is_primary",
    )

    readonly_fields = (
        "preview",
    )

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="150" height="100" '
                'style="object-fit:cover;border-radius:8px;" />',
                obj.image.url,
            )
        return "No Image"

    preview.short_description = "Preview"


class WeeklyTimeSlotInline(nested_admin.NestedTabularInline):
    model = WeeklyTimeSlot
    extra = 1

    fields = (
        "start_time",
        "end_time",
        "minimum_booking_duration_minutes",
        "slot_duration_minutes",
        "buffer_time_minutes",
    )


class WeeklyScheduleInline(nested_admin.NestedStackedInline):
    model = WeeklySchedule
    extra = 1

    fields = (
        "day_of_week",
        "status",
    )

    inlines = [
        WeeklyTimeSlotInline,
    ]


class AvailabilityOverrideInline(
    nested_admin.NestedTabularInline
):
    model = AvailabilityOverride
    extra = 1

    fields = (
        "date",
        "status",
        "start_time",
        "end_time",
        "minimum_booking_duration_minutes",
        "slot_duration_minutes",
        "buffer_time_minutes",
    )


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
    )

    search_fields = (
        "name",
    )


@admin.register(Venue)
class VenueAdmin(nested_admin.NestedModelAdmin):

    list_display = (
        "id",
        "venue_name",
        "venue_owner",
        "location",
        "price_per_hour",
        "is_active",
    )

    search_fields = (
        "venue_name",
        "location",
        "venue_owner__name",
    )

    list_filter = (
        "is_active",
        "location",
    )

    ordering = (
        "venue_name",
    )

    inlines = [
        VenueImageInline,
        WeeklyScheduleInline,
        AvailabilityOverrideInline,
    ]