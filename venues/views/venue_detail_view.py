from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from venues.models.venue import Venue
from venues.serializers.venue_detail_serializer import VenueDetailSerializer
from venues.permissions import IsCustomer


class VenueDetailView(RetrieveAPIView):
    serializer_class = VenueDetailSerializer
    permission_classes = [IsAuthenticated, IsCustomer]
    queryset = Venue.objects.filter(
        is_active=True,
        is_approved=True
    )