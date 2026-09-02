import uuid

from django.conf import settings
from django.db import models

from venues.models import Venue
from accounts.models import VenueOwner


class PaidService(models.Model):

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="paid_services",
    )

    owner = models.ForeignKey(
        VenueOwner,
        on_delete=models.CASCADE,
        related_name="paid_services",
    )

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.name} - {self.venue.venue_name}"


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

    # Final amount charged for this booking.
    # This is frozen when the booking is created.
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
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
        return str(self.booking_id)


class BookingService(models.Model):

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="booking_services",
    )

    service = models.ForeignKey(
        PaidService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_records",
    )

    # Snapshot of the service name at booking time.
    service_name = models.CharField(
        max_length=100,
    )

    # Snapshot of the price at booking time.
    service_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.service_name} - "
            f"{self.booking.booking_id}"
        )