from rest_framework.generics import ListAPIView

from venues.models.venue import Venue
from venues.serializers.venue_list_serializer import VenueListSerializer
from venues.permissions import IsCustomer
from rest_framework.permissions import IsAuthenticated


class VenueListView(ListAPIView):
    serializer_class = VenueListSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    queryset = Venue.objects.filter(
        is_active=True,
        is_approved=True
    )