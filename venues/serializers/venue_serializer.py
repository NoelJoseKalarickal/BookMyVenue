from rest_framework import serializers
from venues.models import Venue


class VenueSerializer(serializers.ModelSerializer):

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
            "contact_number",
            "amenities",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]