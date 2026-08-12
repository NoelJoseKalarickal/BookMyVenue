from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import VenueOwner
from venues.models import WeeklyTimeSlot


class DeleteWeeklyTimeSlotView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, slot_id):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {"message": "Only venue owners can delete slots."},
                status=status.HTTP_403_FORBIDDEN,
            )

        slot = WeeklyTimeSlot.objects.filter(
            id=slot_id,
            weekly_schedule__venue__venue_owner=venue_owner,
        ).first()

        if slot is None:
            return Response(
                {"message": "Time slot not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        slot.delete()

        return Response(
            {"message": "Time slot deleted successfully."},
            status=status.HTTP_200_OK,
        )