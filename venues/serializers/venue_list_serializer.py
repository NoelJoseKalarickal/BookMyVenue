from rest_framework import serializers
from venues.models.venue import Venue


class VenueListSerializer(serializers.ModelSerializer):
    event_types = serializers.StringRelatedField(many=True)

    class Meta:
        model = Venue
        fields = [
            "id",
            "venue_name",
            "description",
            "location",
            "price_per_hour",
            "event_types",
        ]