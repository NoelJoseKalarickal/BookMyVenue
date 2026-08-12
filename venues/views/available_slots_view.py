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


class AvailableSlotsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, venue_id):

        venue = Venue.objects.filter(
            id=venue_id
        ).first()

        if venue is None:
            return Response(
                {
                    "message": "Venue not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        date_string = request.query_params.get(
            "date"
        )

        if not date_string:
            return Response(
                {
                    "message": "date is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            requested_date = datetime.strptime(
                date_string,
                "%Y-%m-%d"
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
                {
                    "message": "Past dates cannot be selected."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =================================================
        # SPECIAL DATE OVERRIDE
        # =================================================

        override = AvailabilityOverride.objects.filter(
            venue=venue,
            date=requested_date,
        ).first()

        if override:

            if override.status == "CLOSED":

                return Response(
                    {
                        "venue": venue.venue_name,
                        "date": requested_date,
                        "slot_duration_minutes": None,
                        "minimum_booking_duration_minutes": None,
                        "slots": [],
                    },
                    status=status.HTTP_200_OK,
                )

            generated = self.generate_slots(
                requested_date,
                override.start_time,
                override.end_time,
                override.slot_duration_minutes,
                override.minimum_booking_duration_minutes,
                override.buffer_time_minutes,
            )

            return Response(
                {
                    "venue": venue.venue_name,
                    "date": requested_date,
                    "slot_duration_minutes":
                        override.slot_duration_minutes,
                    "minimum_booking_duration_minutes":
                        override.minimum_booking_duration_minutes,
                    "slots": generated,
                },
                status=status.HTTP_200_OK,
            )

        # =================================================
        # WEEKLY SCHEDULE
        # =================================================

        day_name = requested_date.strftime(
            "%A"
        ).upper()

        schedule = WeeklySchedule.objects.filter(
            venue=venue,
            day_of_week=day_name,
            status="AVAILABLE",
        ).first()

        if schedule is None:

            return Response(
                {
                    "venue": venue.venue_name,
                    "date": requested_date,
                    "slot_duration_minutes": None,
                    "minimum_booking_duration_minutes": None,
                    "slots": [],
                },
                status=status.HTTP_200_OK,
            )

        all_slots = []

        for time_slot in schedule.time_slots.all():

            generated = self.generate_slots(
                requested_date,
                time_slot.start_time,
                time_slot.end_time,
                time_slot.slot_duration_minutes,
                time_slot.minimum_booking_duration_minutes,
                time_slot.buffer_time_minutes,
            )

            all_slots.extend(generated)

        # =================================================
        # SORT ALL PERIODS
        # =================================================

        all_slots.sort(
            key=lambda slot: slot["start_time"]
        )

        slot_duration = None
        minimum_duration = None

        if schedule.time_slots.exists():

            first_slot = schedule.time_slots.first()

            slot_duration = (
                first_slot.slot_duration_minutes
            )

            minimum_duration = (
                first_slot.minimum_booking_duration_minutes
            )

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

    # =====================================================
    # SLOT GENERATION
    # =====================================================

    def generate_slots(
        self,
        requested_date,
        start_time,
        end_time,
        slot_duration,
        minimum_booking_duration,
        buffer_time,
    ):

        slots = []

        period_start = datetime.combine(
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

        current = period_start

        now = timezone.localtime()

        while current + duration <= period_end:

            slot_end = current + duration

            # ---------------------------------------------
            # CHECK WHETHER MINIMUM BOOKING CAN FIT
            # ---------------------------------------------

            minimum_end = (
                current
                + timedelta(
                    minutes=minimum_booking_duration
                )
            )

            minimum_can_fit = (
                minimum_end <= period_end
            )

            # ---------------------------------------------
            # EXPIRED
            # ---------------------------------------------

            if requested_date < now.date():

                slot_status = "EXPIRED"
                bookable = False

            elif requested_date == now.date():

                if slot_end <= now.replace(
                    second=0,
                    microsecond=0
                ).replace(
                    year=requested_date.year,
                    month=requested_date.month,
                    day=requested_date.day,
                ):

                    slot_status = "EXPIRED"
                    bookable = False

                else:

                    slot_status = "AVAILABLE"
                    bookable = minimum_can_fit

            else:

                slot_status = "AVAILABLE"
                bookable = minimum_can_fit

            slots.append(
                {
                    "start_time": current.strftime(
                        "%H:%M:%S"
                    ),
                    "end_time": slot_end.strftime(
                        "%H:%M:%S"
                    ),
                    "status": slot_status,
                    "bookable": bookable,
                }
            )

            # ---------------------------------------------
            # BUFFER ONLY BETWEEN POSSIBLE START SLOTS
            # ---------------------------------------------

            current = (
                slot_end
                + timedelta(
                    minutes=buffer_time
                )
            )

        return slots