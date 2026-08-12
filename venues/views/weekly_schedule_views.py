from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from venues.models import Venue, WeeklySchedule
from venues.serializers import WeeklyScheduleSerializer


class WeeklyScheduleView(APIView):

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

        schedules = WeeklySchedule.objects.filter(
            venue=venue
        ).prefetch_related(
            "time_slots"
        )

        serializer = WeeklyScheduleSerializer(
            schedules,
            many=True
        )

        return Response(
            {
                "venue": venue.venue_name,
                "schedule": serializer.data,
            },
            status=status.HTTP_200_OK,
        )