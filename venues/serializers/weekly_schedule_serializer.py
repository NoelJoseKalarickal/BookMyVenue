from rest_framework import serializers

from venues.models import WeeklySchedule, WeeklyTimeSlot


class WeeklyTimeSlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = WeeklyTimeSlot
        fields = [
            "id",
            "start_time",
            "end_time",
            "minimum_booking_duration_minutes",
            "slot_duration_minutes",
            "buffer_time_minutes",
        ]

    def validate(self, data):

        start = data.get("start_time")
        end = data.get("end_time")

        if start is not None and end is not None:
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


class WeeklyScheduleSerializer(serializers.ModelSerializer):

    time_slots = WeeklyTimeSlotSerializer(
        many=True
    )

    class Meta:
        model = WeeklySchedule
        fields = [
            "id",
            "venue",
            "day_of_week",
            "status",
            "time_slots",
        ]

    def validate(self, data):

        venue = data.get("venue")
        day = data.get("day_of_week")
        time_slots = data.get("time_slots")

        # -----------------------------------------
        # DUPLICATE VENUE + DAY
        # -----------------------------------------

        if venue and day:

            existing = WeeklySchedule.objects.filter(
                venue=venue,
                day_of_week=day,
            )

            if self.instance:
                existing = existing.exclude(
                    id=self.instance.id
                )

            if existing.exists():
                raise serializers.ValidationError(
                    "A schedule already exists for this venue and day."
                )

        # -----------------------------------------
        # TIME SLOT VALIDATION
        # -----------------------------------------

        if time_slots is not None:

            if not time_slots:
                raise serializers.ValidationError(
                    "At least one time slot is required."
                )

            sorted_slots = sorted(
                time_slots,
                key=lambda slot: slot["start_time"]
            )

            for i in range(len(sorted_slots) - 1):

                current = sorted_slots[i]
                next_slot = sorted_slots[i + 1]

                current_end = current["end_time"]
                next_start = next_slot["start_time"]

                # Overlap
                if current_end > next_start:
                    raise serializers.ValidationError(
                        "Time slots cannot overlap."
                    )

        return data

    def create(self, validated_data):

        time_slots = validated_data.pop(
            "time_slots"
        )

        schedule = WeeklySchedule.objects.create(
            **validated_data
        )

        for slot in time_slots:

            WeeklyTimeSlot.objects.create(
                weekly_schedule=schedule,
                **slot
            )

        return schedule

    def update(self, instance, validated_data):

        time_slots = validated_data.pop(
            "time_slots",
            None
        )

        instance.venue = validated_data.get(
            "venue",
            instance.venue
        )

        instance.day_of_week = validated_data.get(
            "day_of_week",
            instance.day_of_week
        )

        instance.status = validated_data.get(
            "status",
            instance.status
        )

        instance.save()

        if time_slots is not None:

            instance.time_slots.all().delete()

            for slot in time_slots:

                WeeklyTimeSlot.objects.create(
                    weekly_schedule=instance,
                    **slot
                )

        return instance