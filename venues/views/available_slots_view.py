from datetime import datetime, timedelta

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

from bookings.models import Booking


class AvailableSlotsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, venue_id):

        venue = Venue.objects.filter(
            id=venue_id
        ).first()

        if venue is None:
            return Response(
                {"message": "Venue not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        date_string = request.query_params.get("date")

        if not date_string:
            return Response(
                {"message": "date is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            requested_date = datetime.strptime(
                date_string,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            return Response(
                {
                    "message": "Invalid date format. Use YYYY-MM-DD."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.localdate()

        if requested_date < today:
            return Response(
                {"message": "Past dates cannot be selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------
        # GET AVAILABILITY PERIODS
        # -----------------------------------------

        periods = self.get_periods(
            venue,
            requested_date,
        )

        if periods is None:

            return Response(
                {
                    "venue": venue.venue_name,
                    "date": requested_date,
                    "slots": [],
                },
                status=status.HTTP_200_OK,
            )

        all_slots = []

        for period in periods:

            generated = self.generate_slots(
                requested_date,
                period["start_time"],
                period["end_time"],
                period["slot_duration"],
                period["minimum_duration"],
                period["buffer"],
            )

            all_slots.extend(generated)

        all_slots.sort(
            key=lambda slot: slot["start_time"]
        )

        # -----------------------------------------
        # ADD BOOKING STATUS
        # -----------------------------------------

        bookings = Booking.objects.filter(
            venue=venue,
            booking_date=requested_date,
            status__in=[
                "HELD",
                "CONFIRMED",
            ],
        )

        now = timezone.localtime()

        for slot in all_slots:

            slot_start = datetime.strptime(
                slot["start_time"],
                "%H:%M:%S",
            ).time()

            slot_end = datetime.strptime(
                slot["end_time"],
                "%H:%M:%S",
            ).time()

            # BOOKED / HELD takes priority
            for booking in bookings:

                if (
                    booking.start_time < slot_end
                    and booking.end_time > slot_start
                ):

                    if booking.status == "HELD":

                        # Hold expired
                        if (
                            booking.hold_expires_at
                            and booking.hold_expires_at
                            <= timezone.now()
                        ):
                            continue

                        slot["status"] = "HELD"
                        slot["bookable"] = False

                    elif booking.status == "CONFIRMED":

                        slot["status"] = "BOOKED"
                        slot["bookable"] = False

                    break

            # -------------------------------------
            # EXPIRED
            # -------------------------------------

            if (
                slot["status"] == "AVAILABLE"
                and requested_date == now.date()
            ):

                if slot_end <= now.time():

                    slot["status"] = "EXPIRED"
                    slot["bookable"] = False

        # -----------------------------------------
        # RESPONSE
        # -----------------------------------------

        slot_duration = None
        minimum_duration = None

        if periods:

            slot_duration = periods[0][
                "slot_duration"
            ]

            minimum_duration = periods[0][
                "minimum_duration"
            ]

        return Response(
            {
                "venue": venue.venue_name,
                "date": requested_date,
                "slot_duration_minutes": slot_duration,
                "minimum_booking_duration_minutes":
                    minimum_duration,
                "slots": all_slots,
            },
            status=status.HTTP_200_OK,
        )

    # =================================================
    # GET PERIODS
    # =================================================

    def get_periods(
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

            return [
                {
                    "start_time": override.start_time,
                    "end_time": override.end_time,
                    "slot_duration":
                        override.slot_duration_minutes,
                    "minimum_duration":
                        override.minimum_booking_duration_minutes,
                    "buffer":
                        override.buffer_time_minutes,
                }
            ]

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

        periods = []

        for slot in schedule.time_slots.all():

            periods.append(
                {
                    "start_time": slot.start_time,
                    "end_time": slot.end_time,
                    "slot_duration":
                        slot.slot_duration_minutes,
                    "minimum_duration":
                        slot.minimum_booking_duration_minutes,
                    "buffer":
                        slot.buffer_time_minutes,
                }
            )

        return periods

    # =================================================
    # GENERATE SLOTS
    # =================================================

    def generate_slots(
        self,
        requested_date,
        start_time,
        end_time,
        slot_duration,
        minimum_duration,
        buffer,
    ):

        slots = []

        current = datetime.combine(
            requested_date,
            start_time,
        )

        period_end = datetime.combine(
            requested_date,
            end_time,
        )

        duration = timedelta(
            minutes=slot_duration
        )

        while current + duration <= period_end:

            slot_end = current + duration

            minimum_end = (
                current
                + timedelta(
                    minutes=minimum_duration
                )
            )

            can_book = (
                minimum_end <= period_end
            )

            slots.append(
                {
                    "start_time": current.strftime(
                        "%H:%M:%S"
                    ),
                    "end_time": slot_end.strftime(
                        "%H:%M:%S"
                    ),
                    "status": (
                        "AVAILABLE"
                        if can_book
                        else "UNAVAILABLE"
                    ),
                    "bookable": can_book,
                }
            )

            current = (
                slot_end
                + timedelta(
                    minutes=buffer
                )
            )

        return slots