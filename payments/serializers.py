from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = [
            "payment_id",
            "booking",
            "user",
            "amount",
            "razorpay_order_id",
            "razorpay_payment_id",
            "status",
            "refund_id",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "payment_id",
            "user",
            "amount",
            "razorpay_order_id",
            "razorpay_payment_id",
            "status",
            "refund_id",
            "created_at",
            "updated_at",
        ]