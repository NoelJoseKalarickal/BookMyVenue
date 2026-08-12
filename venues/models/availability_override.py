from django.db import models

from .venue import Venue


class AvailabilityOverride(models.Model):

    STATUS_CHOICES = [
        ("AVAILABLE", "Available"),
        ("CLOSED", "Closed"),
    ]

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="availability_overrides",
    )

    date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="AVAILABLE",
    )

    start_time = models.TimeField(
        null=True,
        blank=True,
    )

    end_time = models.TimeField(
        null=True,
        blank=True,
    )

    minimum_booking_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    slot_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    buffer_time_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = (
            "venue",
            "date",
        )

    def __str__(self):
        return f"{self.venue.venue_name} - {self.date}"