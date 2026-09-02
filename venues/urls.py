from django.urls import path

from .views import (
    AddVenueView,
    EventTypeListView,
    VenueListView,
    VenueDetailView,
    UploadVenueImageView,
    SetPrimaryImageView,
    DeleteVenueImageView,
    AddWeeklyScheduleView,
    WeeklyScheduleView,
    EditWeeklyScheduleView,
    DeleteWeeklyTimeSlotView,
    AvailabilityOverrideView,
    CheckAvailabilityView,
    AvailableSlotsView,
)
from venues.views.list_venue_view import VenueListView
urlpatterns = [
    path(
        "",
        VenueListView.as_view(),
        name="venue-list",
    ),

    path(
        "<int:pk>/",
        VenueDetailView.as_view(),
        name="venue-detail",
    ),

    path(
        "add/",
        AddVenueView.as_view(),
        name="add-venue",
    ),

    path(
        "event-types/",
        EventTypeListView.as_view(),
        name="event-types",
    ),

    path(
        "<int:venue_id>/upload-image/",
        UploadVenueImageView.as_view(),
        name="upload-venue-image",
    ),

    path(
        "images/<int:image_id>/set-primary/",
        SetPrimaryImageView.as_view(),
        name="set-primary-image",
    ),

    path(
        "images/<int:image_id>/",
        DeleteVenueImageView.as_view(),
        name="delete-venue-image",
    ),

    path(
        "weekly-schedule/add/",
        AddWeeklyScheduleView.as_view(),
        name="weekly-schedule-add",
    ),

    path(
        "<int:venue_id>/weekly-schedule/",
        WeeklyScheduleView.as_view(),
        name="weekly-schedule",
    ),

    path(
        "weekly-schedule/<int:schedule_id>/",
        EditWeeklyScheduleView.as_view(),
        name="edit-weekly-schedule",
    ),

    path(
        "weekly-schedule/time-slot/<int:slot_id>/",
        DeleteWeeklyTimeSlotView.as_view(),
        name="delete-weekly-time-slot",
    ),
    path(
    "availability-override/add/",
    AvailabilityOverrideView.as_view(),
    name="availability-override-add",
),

path(
    "<int:venue_id>/availability-overrides/",
    AvailabilityOverrideView.as_view(),
    name="availability-overrides",
),
path(
    "<int:venue_id>/check-availability/",
    CheckAvailabilityView.as_view(),
    name="check-availability",
    
),
path(
    "<int:venue_id>/available-slots/",
    AvailableSlotsView.as_view(),
    name="available-slots",
),
path("", VenueListView.as_view(), name="venue-list"),
]