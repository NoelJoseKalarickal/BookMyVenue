from django.contrib import admin
from django.utils.html import format_html

from .models import EventType, Venue, VenueImage


class VenueImageInline(admin.TabularInline):
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
                '<img src="{}" width="150" height="100" style="object-fit:cover;border-radius:8px;" />',
                obj.image.url,
            )
        return "No Image"

    preview.short_description = "Preview"


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
class VenueAdmin(admin.ModelAdmin):
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
    ]