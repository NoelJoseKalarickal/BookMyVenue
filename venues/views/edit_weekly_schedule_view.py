from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import VenueOwner
from venues.models import WeeklySchedule
from venues.serializers import WeeklyScheduleSerializer


class EditWeeklyScheduleView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, schedule_id):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {"message": "Only venue owners can edit schedules."},
                status=status.HTTP_403_FORBIDDEN,
            )

        schedule = WeeklySchedule.objects.filter(
            id=schedule_id,
            venue__venue_owner=venue_owner,
        ).first()

        if schedule is None:
            return Response(
                {"message": "Schedule not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WeeklyScheduleSerializer(
            schedule,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                {
                    "message": "Weekly schedule updated successfully.",
                    "schedule": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )