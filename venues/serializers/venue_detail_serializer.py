from rest_framework import serializers
from venues.models.venue import Venue


class VenueDetailSerializer(serializers.ModelSerializer):
    event_types = serializers.StringRelatedField(many=True)

    class Meta:
        model = Venue
        fields = [
            "id",
            "venue_name",
            "description",
            "location",
            "event_types",
            "capacity",
            "price_per_hour",
            "minimum_booking_hours",
            "amenities",
        ]