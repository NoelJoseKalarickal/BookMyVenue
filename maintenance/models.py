from django.db import models

from venues.models import Venue
from accounts.models import VenueOwner


class Maintenance(models.Model):

    TYPE_CHOICES = [
        ("NORMAL", "Normal"),
        ("EMERGENCY", "Emergency"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("COMPLETED", "Completed"),
    ]

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="maintenance_periods",
    )

    owner = models.ForeignKey(
        VenueOwner,
        on_delete=models.CASCADE,
        related_name="maintenance_requests",
    )

    maintenance_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    start_date = models.DateField()
    start_time = models.TimeField()

    end_date = models.DateField()
    end_time = models.TimeField()

    reason = models.TextField()

    admin_comment = models.TextField(
        blank=True,
        null=True,
    )

    approved_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_maintenance_requests",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
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
            f"{self.maintenance_type} - "
            f"{self.start_date}"
        )


class MaintenanceImage(models.Model):

    maintenance = models.ForeignKey(
        Maintenance,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="maintenance_images/",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"Maintenance Image {self.id}"