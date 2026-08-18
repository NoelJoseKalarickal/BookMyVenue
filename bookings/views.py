from datetime import datetime, timedelta

from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from venues.models import (
    Venue,
    WeeklySchedule,
    AvailabilityOverride,
)

from .models import Booking


class CreateBookingView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        venue_id = request.data.get("venue")
        booking_date = request.data.get("booking_date")
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")

        if not all([
            venue_id,
            booking_date,
            start_time,
            end_time,
        ]):
            return Response(
                {
                    "message": (
                        "venue, booking_date, start_time "
                        "and end_time are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        venue = Venue.objects.filter(
            id=venue_id
        ).first()

        if venue is None:
            return Response(
                {"message": "Venue not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            requested_date = datetime.strptime(
                booking_date,
                "%Y-%m-%d",
            ).date()

            requested_start = datetime.strptime(
                start_time,
                "%H:%M:%S",
            ).time()

            requested_end = datetime.strptime(
                end_time,
                "%H:%M:%S",
            ).time()

        except ValueError:
            return Response(
                {
                    "message": (
                        "Invalid date/time format. "
                        "Use YYYY-MM-DD and HH:MM:SS."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if requested_start >= requested_end:
            return Response(
                {
                    "message": "Start time must be before end time."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.localtime()

        if requested_date < now.date():
            return Response(
                {"message": "Cannot book a past date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            requested_date == now.date()
            and requested_start <= now.time()
        ):
            return Response(
                {
                    "message": (
                        "This booking time has already "
                        "started or expired."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Process expired holds for this exact requested period.
        self.expire_holds(
            venue,
            requested_date,
            requested_start,
            requested_end,
        )

        availability = self.get_availability(
            venue,
            requested_date,
        )

        if availability is None:
            return Response(
                {
                    "message": (
                        "Venue is not available "
                        "on this date."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        duration = (
            datetime.combine(
                requested_date,
                requested_end,
            )
            - datetime.combine(
                requested_date,
                requested_start,
            )
        )

        duration_minutes = int(
            duration.total_seconds() / 60
        )

        if duration_minutes < availability["minimum_duration"]:
            return Response(
                {
                    "message": (
                        "Booking duration is below "
                        "the minimum required duration."
                    ),
                    "minimum_booking_duration_minutes":
                        availability["minimum_duration"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not self.time_is_available(
            availability["slots"],
            requested_start,
            requested_end,
        ):
            return Response(
                {
                    "message": (
                        "Requested time is outside "
                        "the venue's availability."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # SAME USER DUPLICATE / OVERLAPPING BOOKING
        # -------------------------------------------------

        own_conflict = Booking.objects.select_for_update().filter(
            user=request.user,
            venue=venue,
            booking_date=requested_date,
            start_time__lt=requested_end,
            end_time__gt=requested_start,
            status__in=[
                "WAITING",
                "HELD",
                "CONFIRMED",
            ],
        ).first()

        if own_conflict:
            return Response(
                {
                    "message": (
                        "You already have an active booking "
                        "or queue entry for an overlapping time."
                    ),
                    "booking_id": str(
                        own_conflict.booking_id
                    ),
                    "status": own_conflict.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # BUFFER + BOOKING CONFLICT CHECK
        # -------------------------------------------------

        conflict = self.find_conflict(
            request.user,
            venue,
            requested_date,
            requested_start,
            requested_end,
            availability["buffer"],
        )

        if conflict:

            waiting_count = Booking.objects.filter(
                venue=venue,
                booking_date=requested_date,
                status="WAITING",
            ).filter(
                start_time__lt=requested_end,
                end_time__gt=requested_start,
            ).count()

            booking = Booking.objects.create(
                user=request.user,
                venue=venue,
                booking_date=requested_date,
                start_time=requested_start,
                end_time=requested_end,
                status="WAITING",
                queue_position=waiting_count + 1,
                payment_status="PENDING",
            )

            return Response(
                {
                    "message": (
                        "The requested period overlaps "
                        "with an active booking. "
                        "You have been added to the FCFS queue."
                    ),
                    "booking_id": str(
                        booking.booking_id
                    ),
                    "status": booking.status,
                    "queue_position":
                        booking.queue_position,
                },
                status=status.HTTP_201_CREATED,
            )

        # -------------------------------------------------
        # FIRST USER GETS 5-MINUTE HOLD
        # -------------------------------------------------

        hold_expires = (
            timezone.now()
            + timedelta(minutes=5)
        )

        total_amount = (
            venue.price_per_hour
            * (duration_minutes / 60)
        )

        booking = Booking.objects.create(
            user=request.user,
            venue=venue,
            booking_date=requested_date,
            start_time=requested_start,
            end_time=requested_end,
            status="HELD",
            queue_position=1,
            hold_expires_at=hold_expires,
            payment_status="PENDING",
            total_amount=total_amount,
        )

        return Response(
            {
                "message": (
                    "Slot held for 5 minutes. "
                    "You can retry payment any number "
                    "of times within this window."
                ),
                "booking_id": str(
                    booking.booking_id
                ),
                "status": booking.status,
                "queue_position":
                    booking.queue_position,
                "hold_expires_at":
                    booking.hold_expires_at,
                "total_amount":
                    booking.total_amount,
            },
            status=status.HTTP_201_CREATED,
        )

    # =====================================================
    # AVAILABILITY
    # =====================================================

    def get_availability(
        self,
        venue,
        requested_date,
    ):

        override = AvailabilityOverride.objects.filter(
            venue=venue,
            date=requested_date,
        ).first()

        if override:

            if override.status == "CLOSED":
                return None

            return {
                "minimum_duration":
                    override.minimum_booking_duration_minutes
                    or 60,
                "buffer":
                    override.buffer_time_minutes
                    or 0,
                "slots": [
                    (
                        override.start_time,
                        override.end_time,
                    )
                ],
            }

        day_name = requested_date.strftime(
            "%A"
        ).upper()

        schedule = WeeklySchedule.objects.filter(
            venue=venue,
            day_of_week=day_name,
            status="AVAILABLE",
        ).first()

        if schedule is None:
            return None

        slots = []
        minimum_duration = None
        buffer = 0

        for slot in schedule.time_slots.all():

            slots.append(
                (
                    slot.start_time,
                    slot.end_time,
                )
            )

            if minimum_duration is None:
                minimum_duration = (
                    slot.minimum_booking_duration_minutes
                )

            buffer = max(
                buffer,
                slot.buffer_time_minutes or 0,
            )

        return {
            "minimum_duration":
                minimum_duration or 60,
            "buffer": buffer,
            "slots": slots,
        }

    # =====================================================
    # CHECK PERIOD IS WITHIN AVAILABILITY
    # =====================================================

    def time_is_available(
        self,
        slots,
        requested_start,
        requested_end,
    ):

        for slot_start, slot_end in slots:

            if (
                requested_start >= slot_start
                and requested_end <= slot_end
            ):
                return True

        return False

    # =====================================================
    # FIND BOOKING CONFLICT
    # =====================================================

    def find_conflict(
        self,
        user,
        venue,
        booking_date,
        requested_start,
        requested_end,
        buffer_minutes,
    ):

        active_bookings = Booking.objects.select_for_update().filter(
            venue=venue,
            booking_date=booking_date,
            status__in=[
                "HELD",
                "CONFIRMED",
            ],
        )

        requested_start_dt = datetime.combine(
            booking_date,
            requested_start,
        )

        requested_end_dt = datetime.combine(
            booking_date,
            requested_end,
        )

        for booking in active_bookings:

            existing_start_dt = datetime.combine(
                booking_date,
                booking.start_time,
            )

            existing_end_dt = datetime.combine(
                booking_date,
                booking.end_time,
            )

            # Same user can have consecutive bookings
            # without a buffer.
            if booking.user_id == user.id:

                if (
                    requested_start_dt
                    < existing_end_dt
                    and requested_end_dt
                    > existing_start_dt
                ):
                    return booking

                continue

            # Different users require buffer.
            existing_start_with_buffer = (
                existing_start_dt
                - timedelta(minutes=buffer_minutes)
            )

            existing_end_with_buffer = (
                existing_end_dt
                + timedelta(minutes=buffer_minutes)
            )

            if (
                requested_start_dt
                < existing_end_with_buffer
                and requested_end_dt
                > existing_start_with_buffer
            ):
                return booking

        return None

    # =====================================================
    # EXPIRE HOLDS
    # =====================================================

    def expire_holds(
        self,
        venue,
        booking_date,
        start_time,
        end_time,
    ):

        expired = Booking.objects.select_for_update().filter(
            venue=venue,
            booking_date=booking_date,
            status="HELD",
            hold_expires_at__lte=timezone.now(),
        ).filter(
            start_time__lt=end_time,
            end_time__gt=start_time,
        )

        for booking in expired:

            booking.status = "EXPIRED"
            booking.payment_status = "FAILED"
            booking.hold_expires_at = None

            booking.save()

            self.promote_next_waiting(
                venue,
                booking_date,
                booking.start_time,
                booking.end_time,
            )

    # =====================================================
    # PROMOTE NEXT FCFS USER
    # =====================================================

    def promote_next_waiting(
        self,
        venue,
        booking_date,
        start_time,
        end_time,
    ):

        next_booking = Booking.objects.select_for_update().filter(
            venue=venue,
            booking_date=booking_date,
            status="WAITING",
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).order_by(
            "created_at"
        ).first()

        if next_booking is None:
            return

        next_booking.status = "HELD"
        next_booking.queue_position = 1
        next_booking.hold_expires_at = (
            timezone.now()
            + timedelta(minutes=5)
        )

        next_booking.save()

        waiting = Booking.objects.filter(
            venue=venue,
            booking_date=booking_date,
            status="WAITING",
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).order_by(
            "created_at"
        )

        position = 2

        for waiting_booking in waiting:

            waiting_booking.queue_position = position

            waiting_booking.save(
                update_fields=[
                    "queue_position",
                    "updated_at",
                ]
            )

            position += 1


class ConfirmBookingView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, booking_id):

        booking = Booking.objects.select_for_update().filter(
            booking_id=booking_id,
            user=request.user,
        ).first()

        if booking is None:
            return Response(
                {"message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Same 5-minute window is used for all payment attempts.
        if booking.status != "HELD":
            return Response(
                {
                    "message": (
                        "This booking is no longer "
                        "available for payment."
                    ),
                    "status": booking.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Late payment is rejected.
        if (
            booking.hold_expires_at is None
            or booking.hold_expires_at <= timezone.now()
        ):

            booking.status = "EXPIRED"
            booking.payment_status = "FAILED"
            booking.hold_expires_at = None
            booking.save()

            self.promote_next_waiting(
                booking
            )

            return Response(
                {
                    "message": (
                        "The 5-minute booking window "
                        "has expired. Payment cannot "
                        "confirm this booking."
                    ),
                    "status": "EXPIRED",
                    "refund_required": True,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # In the real payment gateway, payment verification
        # happens here. For now this endpoint represents
        # a successful payment.
        booking.payment_status = "SUCCESS"
        booking.status = "CONFIRMED"
        booking.hold_expires_at = None

        booking.save()

        self.send_confirmation_email(
            booking
        )

        return Response(
            {
                "message": (
                    "Booking confirmed successfully."
                ),
                "booking_id": str(
                    booking.booking_id
                ),
                "status": booking.status,
                "payment_status":
                    booking.payment_status,
                "total_amount":
                    booking.total_amount,
            },
            status=status.HTTP_200_OK,
        )

    def promote_next_waiting(self, booking):

        next_booking = Booking.objects.select_for_update().filter(
            venue=booking.venue,
            booking_date=booking.booking_date,
            status="WAITING",
            start_time__lt=booking.end_time,
            end_time__gt=booking.start_time,
        ).order_by(
            "created_at"
        ).first()

        if next_booking:

            next_booking.status = "HELD"
            next_booking.queue_position = 1
            next_booking.hold_expires_at = (
                timezone.now()
                + timedelta(minutes=5)
            )

            next_booking.save()

    def send_confirmation_email(
        self,
        booking,
    ):

        email = booking.user.email

        if not email:
            return

        send_mail(
            subject="BookMyVenue Booking Confirmation",
            message=(
                "Your booking has been confirmed.\n\n"
                f"Booking ID: {booking.booking_id}\n"
                f"Venue: {booking.venue.venue_name}\n"
                f"Date: {booking.booking_date}\n"
                f"Time: {booking.start_time} - "
                f"{booking.end_time}\n"
                f"Amount: {booking.total_amount}\n"
            ),
            from_email=None,
            recipient_list=[email],
            fail_silently=True,
        )


class CancelBookingView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, booking_id):

        booking = Booking.objects.select_for_update().filter(
            booking_id=booking_id,
            user=request.user,
        ).first()

        if booking is None:
            return Response(
                {"message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if booking.status not in [
            "HELD",
            "CONFIRMED",
        ]:
            return Response(
                {
                    "message": (
                        "Booking cannot be cancelled."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        was_held = booking.status == "HELD"

        booking.status = "CANCELLED"

        if booking.payment_status == "SUCCESS":
            booking.payment_status = "REFUNDED"

        booking.hold_expires_at = None

        booking.save()

        # If a HELD user voluntarily cancels,
        # the next FCFS user gets the slot.
        if was_held:

            next_booking = Booking.objects.select_for_update().filter(
                venue=booking.venue,
                booking_date=booking.booking_date,
                status="WAITING",
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time,
            ).order_by(
                "created_at"
            ).first()

            if next_booking:

                next_booking.status = "HELD"
                next_booking.queue_position = 1
                next_booking.hold_expires_at = (
                    timezone.now()
                    + timedelta(minutes=5)
                )

                next_booking.save()

        return Response(
            {
                "message": (
                    "Booking cancelled successfully."
                ),
                "booking_id": str(
                    booking.booking_id
                ),
                "status": booking.status,
                "payment_status":
                    booking.payment_status,
            },
            status=status.HTTP_200_OK,
        )


class ProcessExpiredBookingsView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        now = timezone.now()

        expired_bookings = Booking.objects.select_for_update().filter(
            status="HELD",
            hold_expires_at__lte=now,
        )

        promoted = []

        for booking in expired_bookings:

            booking.status = "EXPIRED"
            booking.payment_status = "FAILED"
            booking.hold_expires_at = None

            booking.save()

            next_booking = Booking.objects.select_for_update().filter(
                venue=booking.venue,
                booking_date=booking.booking_date,
                status="WAITING",
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time,
            ).order_by(
                "created_at"
            ).first()

            if next_booking:

                next_booking.status = "HELD"
                next_booking.queue_position = 1
                next_booking.hold_expires_at = (
                    timezone.now()
                    + timedelta(minutes=5)
                )

                next_booking.save()

                promoted.append(
                    {
                        "expired_booking_id": str(
                            booking.booking_id
                        ),
                        "new_held_booking_id": str(
                            next_booking.booking_id
                        ),
                    }
                )

        return Response(
            {
                "message": (
                    "Expired bookings processed."
                ),
                "promoted": promoted,
            },
            status=status.HTTP_200_OK,
        )