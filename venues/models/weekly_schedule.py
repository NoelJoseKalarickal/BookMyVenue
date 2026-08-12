from django.db import models

from .venue import Venue


class WeeklySchedule(models.Model):

    DAYS = [
        ("MONDAY", "Monday"),
        ("TUESDAY", "Tuesday"),
        ("WEDNESDAY", "Wednesday"),
        ("THURSDAY", "Thursday"),
        ("FRIDAY", "Friday"),
        ("SATURDAY", "Saturday"),
        ("SUNDAY", "Sunday"),
    ]

    STATUS_CHOICES = [
        ("AVAILABLE", "Available"),
        ("CLOSED", "Closed"),
    ]

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="weekly_schedules",
    )

    day_of_week = models.CharField(
        max_length=20,
        choices=DAYS,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="AVAILABLE",
    )

    class Meta:
        unique_together = (
            "venue",
            "day_of_week",
        )
        ordering = [
            "venue",
            "day_of_week",
        ]

    def __str__(self):
        return f"{self.venue.venue_name} - {self.day_of_week}"