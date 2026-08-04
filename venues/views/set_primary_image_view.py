from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import VenueOwner
from venues.models import VenueImage


class SetPrimaryImageView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, image_id):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {"message": "Only venue owners can perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        image = VenueImage.objects.filter(
            id=image_id,
            venue__venue_owner=venue_owner
        ).first()

        if image is None:
            return Response(
                {"message": "Image not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        VenueImage.objects.filter(
            venue=image.venue
        ).update(is_primary=False)

        image.is_primary = True
        image.save()

        return Response(
            {"message": "Cover image updated successfully."},
            status=status.HTTP_200_OK
        )