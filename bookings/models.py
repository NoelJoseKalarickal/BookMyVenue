import uuid

from django.conf import settings
from django.db import models

from venues.models import Venue


class Booking(models.Model):

    STATUS_CHOICES = [
        ("WAITING", "Waiting"),
        ("HELD", "Held"),
        ("CONFIRMED", "Confirmed"),
        ("PAYMENT_FAILED", "Payment Failed"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    booking_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    booking_date = models.DateField()

    start_time = models.TimeField()

    end_time = models.TimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="WAITING",
    )

    queue_position = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    hold_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="PENDING",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return str(self.booking_id)