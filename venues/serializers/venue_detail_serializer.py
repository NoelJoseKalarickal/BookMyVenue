from django.utils import timezone

from rest_framework import serializers

from venues.models import Venue

from maintenance.services import (
    get_current_maintenance,
)


class VenueDetailSerializer(
    serializers.ModelSerializer
):

    event_types = serializers.StringRelatedField(
        many=True
    )

    images = serializers.SerializerMethodField()

    maintenance_status = serializers.SerializerMethodField()

    maintenance_reason = serializers.SerializerMethodField()

    maintenance_end = serializers.SerializerMethodField()

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
            "maintenance_status",
            "maintenance_reason",
            "maintenance_end",
        ]

    def get_images(self, obj):

        return [
            image.image.url
            for image in obj.images.all()
        ]

    def get_current(
        self,
        obj,
    ):

        now = timezone.localtime()

        return get_current_maintenance(
            obj,
            now.date(),
            now.time(),
        )

    def get_maintenance_status(
        self,
        obj,
    ):

        if self.get_current(obj):
            return "UNDER_MAINTENANCE"

        return "AVAILABLE"

    def get_maintenance_reason(
        self,
        obj,
    ):

        maintenance = self.get_current(obj)

        if maintenance:
            return maintenance.reason

        return None

    def get_maintenance_end(
        self,
        obj,
    ):

        maintenance = self.get_current(obj)

        if maintenance:

            return (
                f"{maintenance.end_date} "
                f"{maintenance.end_time}"
            )

        return None