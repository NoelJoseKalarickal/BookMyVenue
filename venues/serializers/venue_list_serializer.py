from django.utils import timezone

from rest_framework import serializers

from venues.models import Venue

from maintenance.services import (
    get_current_maintenance,
)


class VenueListSerializer(
    serializers.ModelSerializer
):

    event_types = serializers.StringRelatedField(
        many=True
    )

    cover_image = serializers.SerializerMethodField()

    maintenance_status = serializers.SerializerMethodField()

    maintenance_end = serializers.SerializerMethodField()

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
            "maintenance_status",
            "maintenance_end",
        ]

    def get_cover_image(self, obj):

        image = obj.images.filter(
            is_primary=True
        ).first()

        if image:
            return image.image.url

        return None

    def get_maintenance_status(
        self,
        obj,
    ):

        now = timezone.localtime()

        maintenance = get_current_maintenance(
            obj,
            now.date(),
            now.time(),
        )

        if maintenance:
            return "UNDER_MAINTENANCE"

        return "AVAILABLE"

    def get_maintenance_end(
        self,
        obj,
    ):

        now = timezone.localtime()

        maintenance = get_current_maintenance(
            obj,
            now.date(),
            now.time(),
        )

        if maintenance:

            return (
                f"{maintenance.end_date} "
                f"{maintenance.end_time}"
            )

        return None