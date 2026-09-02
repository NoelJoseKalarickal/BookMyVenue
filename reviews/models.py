from django.db import models
from django.contrib.auth.models import User

from venues.models import Venue
from bookings.models import Booking


class Review(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("REPORTED", "Reported"),
        ("SUSPENDED", "Suspended"),
    ]

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="review",
    )

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="venue_reviews",
    )

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    rating = models.PositiveIntegerField()

    comment = models.TextField()

    owner_reply = models.TextField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )

    report_reason = models.TextField(
        blank=True,
        null=True,
    )

    reported_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    suspended_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.venue.venue_name} - "
            f"{self.customer.username} - "
            f"{self.rating}/5"
        )