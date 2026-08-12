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
from .serializers import BookingSerializer


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
                    "message": "Invalid date or time format."
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
                {
                    "message": "Cannot book a past date."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            requested_date == now.date()
            and requested_start <= now.time()
        ):
            return Response(
                {
                    "message": "This booking time has already started or expired."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # REMOVE EXPIRED HOLDS
        # -------------------------------------------------

        self.expire_old_holds(
            venue,
            requested_date,
            requested_start,
            requested_end,
        )

        # -------------------------------------------------
        # CHECK VENUE AVAILABILITY
        # -------------------------------------------------

        availability = self.get_availability(
            venue,
            requested_date,
        )

        if availability is None:
            return Response(
                {
                    "message": "Venue is not available on this date."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        minimum_duration = availability[
            "minimum_booking_duration"
        ]

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

        if duration_minutes < minimum_duration:
            return Response(
                {
                    "message": (
                        "Booking duration is shorter than "
                        "the minimum required duration."
                    ),
                    "minimum_booking_duration_minutes":
                        minimum_duration,
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
        # CHECK EXISTING BOOKINGS / HOLDS
        # -------------------------------------------------

        conflicting = Booking.objects.select_for_update().filter(
            venue=venue,
            booking_date=requested_date,
            start_time__lt=requested_end,
            end_time__gt=requested_start,
            status__in=[
                "HELD",
                "CONFIRMED",
            ],
        )

        if conflicting.exists():

            queue_position = (
                Booking.objects.filter(
                    venue=venue,
                    booking_date=requested_date,
                    start_time=requested_start,
                    end_time=requested_end,
                    status__in=[
                        "WAITING",
                        "HELD",
                    ],
                ).count()
                + 1
            )

            booking = Booking.objects.create(
                user=request.user,
                venue=venue,
                booking_date=requested_date,
                start_time=requested_start,
                end_time=requested_end,
                status="WAITING",
                queue_position=queue_position,
            )

            return Response(
                {
                    "message": (
                        "Slot is currently occupied. "
                        "You have been added to the queue."
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

        hold_expiry = timezone.now() + timedelta(
            minutes=5
        )

        booking = Booking.objects.create(
            user=request.user,
            venue=venue,
            booking_date=requested_date,
            start_time=requested_start,
            end_time=requested_end,
            status="HELD",
            queue_position=1,
            hold_expires_at=hold_expiry,
            payment_status="PENDING",
        )

        return Response(
            {
                "message": (
                    "Slot held successfully. "
                    "Complete payment within 5 minutes."
                ),
                "booking_id": str(
                    booking.booking_id
                ),
                "status": booking.status,
                "queue_position": booking.queue_position,
                "hold_expires_at":
                    booking.hold_expires_at,
            },
            status=status.HTTP_201_CREATED,
        )

    # -----------------------------------------------------
    # AVAILABILITY
    # -----------------------------------------------------

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
                "minimum_booking_duration":
                    override.minimum_booking_duration_minutes,
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

        return {
            "minimum_booking_duration":
                minimum_duration or 60,
            "slots": slots,
        }

    # -----------------------------------------------------
    # CHECK REQUESTED TIME
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # EXPIRE OLD HOLDS
    # -----------------------------------------------------

    def expire_old_holds(
        self,
        venue,
        booking_date,
        start_time,
        end_time,
    ):

        expired = Booking.objects.filter(
            venue=venue,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            status="HELD",
            hold_expires_at__lt=timezone.now(),
        )

        for booking in expired:

            booking.status = "EXPIRED"
            booking.payment_status = "FAILED"
            booking.save(
                update_fields=[
                    "status",
                    "payment_status",
                    "updated_at",
                ]
            )


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
                {
                    "message": "Booking not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if booking.status != "HELD":
            return Response(
                {
                    "message": (
                        "This booking is no longer available "
                        "for confirmation."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            booking.hold_expires_at is None
            or booking.hold_expires_at < timezone.now()
        ):

            booking.status = "EXPIRED"
            booking.payment_status = "FAILED"
            booking.save()

            return Response(
                {
                    "message": "Booking hold has expired."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------------------------
        # PAYMENT SUCCESS
        # ---------------------------------------------

        booking.status = "CONFIRMED"
        booking.payment_status = "SUCCESS"
        booking.hold_expires_at = None
        booking.save()

        self.send_confirmation_email(
            booking
        )

        return Response(
            {
                "message": "Booking confirmed successfully.",
                "booking_id": str(
                    booking.booking_id
                ),
                "status": booking.status,
            },
            status=status.HTTP_200_OK,
        )

    def send_confirmation_email(
        self,
        booking,
    ):

        user_email = getattr(
            booking.user,
            "email",
            None,
        )

        if not user_email:
            return

        send_mail(
            subject="BookMyVenue Booking Confirmation",
            message=(
                f"Your booking has been confirmed.\n\n"
                f"Booking ID: {booking.booking_id}\n"
                f"Venue: {booking.venue.venue_name}\n"
                f"Date: {booking.booking_date}\n"
                f"Time: {booking.start_time} - "
                f"{booking.end_time}\n"
            ),
            from_email=None,
            recipient_list=[
                user_email
            ],
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
                {
                    "message": "Booking not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if booking.status not in [
            "HELD",
            "CONFIRMED",
        ]:
            return Response(
                {
                    "message": "This booking cannot be cancelled."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = "CANCELLED"

        if booking.payment_status == "SUCCESS":
            booking.payment_status = "REFUNDED"

        booking.save()

        return Response(
            {
                "message": "Booking cancelled successfully.",
                "booking_id": str(
                    booking.booking_id
                ),
                "status": booking.status,
            },
            status=status.HTTP_200_OK,
        )