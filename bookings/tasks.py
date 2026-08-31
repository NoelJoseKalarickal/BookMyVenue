from datetime import timedelta

from celery import shared_task

from django.db import transaction
from django.utils import timezone

from .models import Booking
@shared_task
def process_expired_bookings():

    now = timezone.now()

    with transaction.atomic():

        expired_bookings = (
            Booking.objects
            .select_for_update()
            .filter(
                status="HELD",
                hold_expires_at__lte=now,
            )
        )

        for booking in expired_bookings:

            booking.status = "EXPIRED"
            booking.payment_status = "FAILED"
            booking.hold_expires_at = None

            booking.save()

            next_booking = (
                Booking.objects
                .select_for_update()
                .filter(
                    venue=booking.venue,
                    booking_date=booking.booking_date,
                    status="WAITING",
                    start_time__lt=booking.end_time,
                    end_time__gt=booking.start_time,
                )
                .order_by("created_at")
                .first()
            )

            if next_booking:

                next_booking.status = "HELD"
                next_booking.queue_position = 1
                next_booking.hold_expires_at = (
                    timezone.now()
                    + timedelta(minutes=5)
                )

                next_booking.save()

                waiting_bookings = (
                    Booking.objects
                    .filter(
                        venue=booking.venue,
                        booking_date=booking.booking_date,
                        status="WAITING",
                        start_time__lt=booking.end_time,
                        end_time__gt=booking.start_time,
                    )
                    .order_by("created_at")
                )

                position = 2

                for waiting_booking in waiting_bookings:

                    waiting_booking.queue_position = position

                    waiting_booking.save(
                        update_fields=[
                            "queue_position",
                            "updated_at",
                        ]
                    )

                    position += 1

    return "Expired bookings processed."