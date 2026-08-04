from rest_framework import serializers
from venues.models import Venue


class VenueListSerializer(serializers.ModelSerializer):
    event_types = serializers.StringRelatedField(many=True)
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = [
            "id",
            "venue_name",
            "description",
            "location",
            "price_per_hour",
            "event_types",
            "cover_image",
        ]

    def get_cover_image(self, obj):
        image = obj.images.filter(is_primary=True).first()

        if image:
            return image.image.url

        return None