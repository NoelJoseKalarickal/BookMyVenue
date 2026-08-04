from rest_framework import serializers

from venues.models import VenueImage


class VenueImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = VenueImage
        fields = [
            "id",
            "venue",
            "image",
            "is_primary",
        ]

    def validate(self, attrs):

        venue = attrs["venue"]

        image_count = VenueImage.objects.filter(
            venue=venue
        ).count()

        if image_count >= 30:
            raise serializers.ValidationError(
                "A venue can have a maximum of 30 images."
            )

        if attrs.get("is_primary", False):

            if VenueImage.objects.filter(
                venue=venue,
                is_primary=True
            ).exists():

                raise serializers.ValidationError(
                    "A primary image already exists for this venue."
                )

        return attrs 