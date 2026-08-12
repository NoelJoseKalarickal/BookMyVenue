from rest_framework import serializers

from .models import Booking


class BookingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Booking
        fields = [
            "booking_id",
            "user",
            "venue",
            "booking_date",
            "start_time",
            "end_time",
            "status",
            "queue_position",
            "hold_expires_at",
            "payment_status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "booking_id",
            "user",
            "status",
            "queue_position",
            "hold_expires_at",
            "payment_status",
            "created_at",
            "updated_at",
        ]