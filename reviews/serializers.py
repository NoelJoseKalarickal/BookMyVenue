from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):

    customer_name = serializers.CharField(
        source="customer.username",
        read_only=True,
    )

    venue_name = serializers.CharField(
        source="venue.venue_name",
        read_only=True,
    )

    class Meta:
        model = Review

        fields = [
            "id",
            "booking",
            "customer",
            "customer_name",
            "venue",
            "venue_name",
            "rating",
            "comment",
            "owner_reply",
            "status",
            "report_reason",
            "reported_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "customer",
            "customer_name",
            "venue_name",
            "venue",
            "owner_reply",
            "status",
            "report_reason",
            "reported_at",
            "created_at",
            "updated_at",
        ]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )

        return value


class CreateReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = Review

        fields = [
            "booking",
            "rating",
            "comment",
        ]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )

        return value


class UpdateReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = Review

        fields = [
            "rating",
            "comment",
        ]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )

        return value


class OwnerReplySerializer(serializers.Serializer):

    reply = serializers.CharField(
        required=True,
        allow_blank=False,
    )


class ReportReviewSerializer(serializers.Serializer):

    reason = serializers.CharField(
        required=True,
        allow_blank=False,
    )