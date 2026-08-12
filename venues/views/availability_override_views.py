from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import VenueOwner
from venues.models import Venue, AvailabilityOverride
from venues.serializers import AvailabilityOverrideSerializer


class AvailabilityOverrideView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {
                    "message": "Only venue owners can add overrides."
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

        serializer = AvailabilityOverrideSerializer(
            data=request.data
        )

        if serializer.is_valid():
            override = serializer.save()

            return Response(
                {
                    "message": "Availability override added successfully.",
                    "override_id": override.id,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

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

        overrides = AvailabilityOverride.objects.filter(
            venue=venue
        ).order_by("date")

        serializer = AvailabilityOverrideSerializer(
            overrides,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )