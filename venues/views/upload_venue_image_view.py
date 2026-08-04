from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import VenueOwner
from venues.models import Venue, VenueImage
from venues.serializers import VenueImageSerializer


class UploadVenueImageView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, venue_id):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {
                    "message": "Only venue owners can upload images."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        venue = Venue.objects.filter(
            id=venue_id,
            venue_owner=venue_owner
        ).first()

        if venue is None:
            return Response(
                {
                    "message": "Venue not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        images = request.FILES.getlist("image")

        if not images:
            return Response(
                {
                    "message": "Please upload at least one image."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        existing_images = VenueImage.objects.filter(venue=venue).count()

        if existing_images + len(images) > 30:
            return Response(
                {
                    "message": "A venue can have a maximum of 30 images."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        has_primary = VenueImage.objects.filter(
            venue=venue,
            is_primary=True
        ).exists()

        uploaded = []

        for image in images:

            serializer = VenueImageSerializer(
                data={
                    "venue": venue.id,
                    "image": image,
                    "is_primary": not has_primary,
                }
            )

            serializer.is_valid(raise_exception=True)
            serializer.save()

            uploaded.append(serializer.data)

            has_primary = True

        return Response(
            {
                "message": f"{len(uploaded)} image(s) uploaded successfully.",
                "images": uploaded,
            },
            status=status.HTTP_201_CREATED
        )