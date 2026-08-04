from rest_framework import serializers
from venues.models import Venue


class VenueDetailSerializer(serializers.ModelSerializer):
    event_types = serializers.StringRelatedField(many=True)
    images = serializers.SerializerMethodField()

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
            "images",
        ]

    def get_images(self, obj):
        return [
            image.image.url
            for image in obj.images.all()
        ]