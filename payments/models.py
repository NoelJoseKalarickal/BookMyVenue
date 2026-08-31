import uuid

from django.conf import settings
from django.db import models

from bookings.models import Booking


class Payment(models.Model):

    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    payment_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="payment",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    razorpay_order_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    razorpay_payment_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    razorpay_signature = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="CREATED",
    )

    refund_id = models.CharField(
        max_length=255,
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
        return str(self.payment_id)