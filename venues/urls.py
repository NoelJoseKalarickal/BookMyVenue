from django.urls import path
from .views import AddVenueView, EventTypeListView
from venues.views.list_venue_view import VenueListView
from venues.views.venue_detail_view import VenueDetailView

urlpatterns = [
    path("", VenueListView.as_view(), name="venue-list"),
    path("<int:pk>/", VenueDetailView.as_view(), name="venue-detail"),
    path("add/", AddVenueView.as_view(), name="add-venue"),
    path("event-types/", EventTypeListView.as_view(), name="event-types"),
]