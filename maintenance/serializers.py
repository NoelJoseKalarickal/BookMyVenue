from datetime import date, datetime

from rest_framework import serializers

from .models import (
    Maintenance,
    MaintenanceImage,
)


class MaintenanceImageSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = MaintenanceImage

        fields = [
            "id",
            "image",
            "uploaded_at",
        ]

        read_only_fields = [
            "id",
            "uploaded_at",
        ]


class MaintenanceSerializer(
    serializers.ModelSerializer
):

    images = MaintenanceImageSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Maintenance

        fields = [
            "id",
            "venue",
            "owner",
            "maintenance_type",
            "status",
            "start_date",
            "start_time",
            "end_date",
            "end_time",
            "reason",
            "admin_comment",
            "approved_by",
            "approved_at",
            "images",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "owner",
            "status",
            "admin_comment",
            "approved_by",
            "approved_at",
            "images",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):

        start_date = data.get("start_date")
        end_date = data.get("end_date")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        maintenance_type = data.get("maintenance_type")
        reason = data.get("reason")

        if not all([
            start_date,
            end_date,
            start_time,
            end_time,
            maintenance_type,
            reason,
        ]):
            raise serializers.ValidationError(
                "All maintenance fields are required."
            )

        if start_date < date.today():
            raise serializers.ValidationError(
                "Maintenance cannot start in the past."
            )

        start_datetime = datetime.combine(
            start_date,
            start_time,
        )

        end_datetime = datetime.combine(
            end_date,
            end_time,
        )

        if end_datetime <= start_datetime:
            raise serializers.ValidationError(
                "Maintenance end must be after maintenance start."
            )

        if maintenance_type not in [
            "NORMAL",
            "EMERGENCY",
        ]:
            raise serializers.ValidationError(
                "Invalid maintenance type."
            )

        return data


class MaintenanceApprovalSerializer(
    serializers.Serializer
):

    action = serializers.ChoiceField(
        choices=[
            "APPROVE",
            "REJECT",
        ]
    )

    admin_comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )