from datetime import date

from rest_framework import serializers

from venues.models import AvailabilityOverride


class AvailabilityOverrideSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = AvailabilityOverride
        fields = [
            "id",
            "venue",
            "date",
            "status",
            "start_time",
            "end_time",
            "minimum_booking_duration_minutes",
            "slot_duration_minutes",
            "buffer_time_minutes",
        ]

    def validate(self, data):

        override_date = data.get("date")
        status_value = data.get(
            "status",
            "AVAILABLE",
        )

        start = data.get("start_time")
        end = data.get("end_time")

        # -----------------------------------------
        # PAST DATE
        # -----------------------------------------

        if override_date and override_date < date.today():
            raise serializers.ValidationError(
                "Availability override cannot be created for a past date."
            )

        # -----------------------------------------
        # CLOSED
        # -----------------------------------------

        if status_value == "CLOSED":

            data["start_time"] = None
            data["end_time"] = None
            data["minimum_booking_duration_minutes"] = None
            data["slot_duration_minutes"] = None
            data["buffer_time_minutes"] = None

            return data

        # -----------------------------------------
        # AVAILABLE
        # -----------------------------------------

        if not start or not end:
            raise serializers.ValidationError(
                "Start time and end time are required when the date is available."
            )

        if start >= end:
            raise serializers.ValidationError(
                "Start time must be before end time."
            )

        minimum = data.get(
            "minimum_booking_duration_minutes",
            60,
        )

        slot_duration = data.get(
            "slot_duration_minutes",
            60,
        )

        buffer = data.get(
            "buffer_time_minutes",
            0,
        )

        if minimum <= 0:
            raise serializers.ValidationError(
                "Minimum booking duration must be greater than 0."
            )

        if slot_duration <= 0:
            raise serializers.ValidationError(
                "Slot duration must be greater than 0."
            )

        if minimum > slot_duration:
            raise serializers.ValidationError(
                "Minimum booking duration cannot be greater than slot duration."
            )

        if buffer < 0:
            raise serializers.ValidationError(
                "Buffer time cannot be negative."
            )

        return data