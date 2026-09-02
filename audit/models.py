from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):

    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("BOOKING_CREATED", "Booking Created"),
        ("BOOKING_CANCELLED", "Booking Cancelled"),
        ("PAYMENT_SUCCESS", "Payment Success"),
        ("PAYMENT_REFUND", "Payment Refund"),
        ("MAINTENANCE_CREATED", "Maintenance Created"),
        ("EMERGENCY_MAINTENANCE", "Emergency Maintenance"),
        ("REVIEW_REPORTED", "Review Reported"),
        ("REVIEW_SUSPENDED", "Review Suspended"),
        ("REVIEW_RESTORED", "Review Restored"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
    )

    description = models.TextField()

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        username = (
            self.user.username
            if self.user
            else "System"
        )

        return f"{username} - {self.action}"