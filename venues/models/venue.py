from django.db import models
from accounts.models import VenueOwner
from .event_type import EventType


class Venue(models.Model):
    venue_owner = models.ForeignKey(
        VenueOwner,
        on_delete=models.CASCADE,
        related_name="venues"
    )

    venue_name = models.CharField(max_length=100)

    description = models.TextField()

    location = models.CharField(max_length=255)

    event_types = models.ManyToManyField(
        EventType,
        related_name="venues"
    )

    capacity = models.PositiveIntegerField()

    price_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    minimum_booking_hours = models.PositiveIntegerField(default=1)

    contact_number = models.CharField(max_length=15)

    amenities = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    is_approved = models.BooleanField(default=False)

    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )

    total_reviews = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.venue_name