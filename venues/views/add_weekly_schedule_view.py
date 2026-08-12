from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import VenueOwner
from venues.models import Venue
from venues.serializers import WeeklyScheduleSerializer


class AddWeeklyScheduleView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {
                    "message": "Only venue owners can add schedules."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        venue = Venue.objects.filter(
            id=request.data.get("venue"),
            venue_owner=venue_owner,
        ).first()

        if venue is None:
            return Response(
                {
                    "message": "Venue not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        days = request.data.get("days", [])

        if not days:
            return Response(
                {
                    "message": "Please select at least one day."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []

        for day in days:

            data = {
                "venue": venue.id,
                "day_of_week": day,
                "status": request.data.get(
                    "status",
                    "AVAILABLE",
                ),
                "time_slots": request.data.get(
                    "time_slots",
                    [],
                ),
            }

            serializer = WeeklyScheduleSerializer(data=data)

            if serializer.is_valid():

                schedule = serializer.save()

                created.append(schedule.id)

            else:

                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {
                "message": "Weekly schedule added successfully.",
                "created_schedule_ids": created,
            },
            status=status.HTTP_201_CREATED,
        )