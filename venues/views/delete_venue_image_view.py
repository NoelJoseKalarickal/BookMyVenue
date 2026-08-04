from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import VenueOwner
from venues.models import VenueImage


class DeleteVenueImageView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, image_id):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {
                    "message": "Only venue owners can delete images."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        image = VenueImage.objects.filter(
            id=image_id,
            venue__venue_owner=venue_owner
        ).first()

        if image is None:
            return Response(
                {
                    "message": "Image not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        venue = image.venue
        was_primary = image.is_primary

        image.delete()

        if was_primary:

            new_primary = VenueImage.objects.filter(
                venue=venue
            ).first()

            if new_primary:
                new_primary.is_primary = True
                new_primary.save()

        return Response(
            {
                "message": "Image deleted successfully."
            },
            status=status.HTTP_200_OK
        )