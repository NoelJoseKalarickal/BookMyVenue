from django.urls import path
from .views import (
    AddVenueView,
    EventTypeListView,
    VenueListView,
    VenueDetailView,
    UploadVenueImageView,
    SetPrimaryImageView,
    DeleteVenueImageView,
)
urlpatterns = [
    path("", VenueListView.as_view(), name="venue-list"),
    path("<int:pk>/", VenueDetailView.as_view(), name="venue-detail"),
    path("add/", AddVenueView.as_view(), name="add-venue"),
    path("event-types/", EventTypeListView.as_view(), name="event-types"),
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
    

]