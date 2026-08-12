from datetime import date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from venues.models import (
    Venue,
    WeeklySchedule,
    AvailabilityOverride,
)


class CheckAvailabilityView(APIView):

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

        requested_date = request.query_params.get("date")
        start_time = request.query_params.get("start_time")
        end_time = request.query_params.get("end_time")

        if not requested_date or not start_time or not end_time:
            return Response(
                {
                    "message": "date, start_time and end_time are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            requested_date = date.fromisoformat(
                requested_date
            )
        except ValueError:
            return Response(
                {"message": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if requested_date < date.today():
            return Response(
                {"message": "Past dates cannot be selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check special-date override first
        override = AvailabilityOverride.objects.filter(
            venue=venue,
            date=requested_date,
        ).first()

        if override:

            if override.status == "CLOSED":
                return Response(
                    {
                        "available": False,
                        "message": "Venue is closed on this date.",
                    },
                    status=status.HTTP_200_OK,
                )

            schedule_start = override.start_time
            schedule_end = override.end_time

        else:

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
                        "available": False,
                        "message": "Venue is not available on this day.",
                    },
                    status=status.HTTP_200_OK,
                )

            slots = schedule.time_slots.all()

            for slot in slots:

                if (
                    str(slot.start_time) <= start_time
                    and str(slot.end_time) >= end_time
                ):
                    return Response(
                        {
                            "available": True,
                            "message": "Venue is available.",
                        },
                        status=status.HTTP_200_OK,
                    )

            return Response(
                {
                    "available": False,
                    "message": "Requested time is outside venue availability.",
                },
                status=status.HTTP_200_OK,
            )

        if (
            str(schedule_start) <= start_time
            and str(schedule_end) >= end_time
        ):
            return Response(
                {
                    "available": True,
                    "message": "Venue is available.",
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "available": False,
                "message": "Requested time is outside venue availability.",
            },
            status=status.HTTP_200_OK,
        )