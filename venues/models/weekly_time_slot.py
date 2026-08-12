from django.db import models

from .weekly_schedule import WeeklySchedule


class WeeklyTimeSlot(models.Model):

    weekly_schedule = models.ForeignKey(
        WeeklySchedule,
        on_delete=models.CASCADE,
        related_name="time_slots",
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    minimum_booking_duration_minutes = models.PositiveIntegerField(
        default=60,
    )

    slot_duration_minutes = models.PositiveIntegerField(
        default=60,
    )

    buffer_time_minutes = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "start_time",
        ]

    def __str__(self):
        return (
            f"{self.weekly_schedule.day_of_week} "
            f"{self.start_time}-{self.end_time}"
        )