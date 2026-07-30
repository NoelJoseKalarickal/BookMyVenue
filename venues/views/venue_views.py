from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


from accounts.models import VenueOwner

from venues.serializers import VenueSerializer


class AddVenueView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        venue_owner = VenueOwner.objects.filter(user=request.user).first()

        if venue_owner is None:
            return Response(
                {"message": "Only venue owners can add venues."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = VenueSerializer(data=request.data)

        if serializer.is_valid():

            serializer.save(
                venue_owner=venue_owner,
                is_approved=False
            )

            return Response(
                {
                    "message": "Venue submitted successfully. Waiting for admin approval."
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )