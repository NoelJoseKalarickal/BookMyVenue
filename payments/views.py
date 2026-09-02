import razorpay

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from bookings.models import Booking
from accounts.models import VenueOwner

from audit.services import create_audit_log

from .models import Payment
from .serializers import PaymentSerializer
from payments.route_service import transfer_payment_to_owner


class CreatePaymentOrderView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, booking_id):

        booking = Booking.objects.select_for_update().filter(
            booking_id=booking_id,
            user=request.user,
        ).first()

        if booking is None:
            return Response(
                {"message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if booking.status != "HELD":
            return Response(
                {
                    "message": (
                        "Payment can only be made for "
                        "a booking that is currently held."
                    ),
                    "status": booking.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            booking.hold_expires_at is None
            or booking.hold_expires_at <= timezone.now()
        ):
            return Response(
                {
                    "message": (
                        "The 5-minute payment window "
                        "has expired."
                    ),
                    "status": "EXPIRED",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.total_amount is None:
            return Response(
                {
                    "message": (
                        "Booking does not have a valid "
                        "payment amount."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_payment = Payment.objects.filter(
            booking=booking,
        ).first()

        if (
            existing_payment
            and existing_payment.razorpay_order_id
        ):
            return Response(
                {
                    "message": "Payment order already exists.",
                    "payment": PaymentSerializer(
                        existing_payment
                    ).data,
                    "razorpay_key_id":
                        settings.RAZORPAY_KEY_ID,
                    "razorpay_order_id":
                        existing_payment.razorpay_order_id,
                    "amount":
                        int(booking.total_amount * 100),
                    "currency": "INR",
                    "hold_expires_at":
                        booking.hold_expires_at,
                },
                status=status.HTTP_200_OK,
            )

        if (
            not settings.RAZORPAY_KEY_ID
            or not settings.RAZORPAY_KEY_SECRET
        ):
            return Response(
                {
                    "message": (
                        "Razorpay credentials are not configured."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

        amount_paise = int(
            booking.total_amount * 100
        )

        try:
            razorpay_order = client.order.create(
                {
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": str(
                        booking.booking_id
                    ),
                }
            )

        except Exception:
            return Response(
                {
                    "message": (
                        "Unable to create Razorpay order."
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment, created = Payment.objects.get_or_create(
            booking=booking,
            defaults={
                "user": request.user,
                "amount": booking.total_amount,
            },
        )

        payment.razorpay_order_id = (
            razorpay_order["id"]
        )
        payment.amount = booking.total_amount
        payment.status = "CREATED"
        payment.save()

        create_audit_log(
            request,
            "CREATE",
            (
                f"Razorpay payment order created for "
                f"booking {booking.booking_id}, "
                f"amount ₹{booking.total_amount}."
            ),
        )

        return Response(
            {
                "message": (
                    "Payment order created successfully."
                ),
                "payment": PaymentSerializer(
                    payment
                ).data,
                "razorpay_key_id":
                    settings.RAZORPAY_KEY_ID,
                "razorpay_order_id":
                    razorpay_order["id"],
                "amount":
                    amount_paise,
                "currency": "INR",
                "hold_expires_at":
                    booking.hold_expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyPaymentView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, booking_id):

        booking = Booking.objects.select_for_update().filter(
            booking_id=booking_id,
            user=request.user,
        ).first()

        if booking is None:
            return Response(
                {"message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payment = Payment.objects.select_for_update().filter(
            booking=booking,
            user=request.user,
        ).first()

        if payment is None:
            return Response(
                {
                    "message": "Payment order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        razorpay_payment_id = request.data.get(
            "razorpay_payment_id"
        )

        razorpay_order_id = request.data.get(
            "razorpay_order_id"
        )

        razorpay_signature = request.data.get(
            "razorpay_signature"
        )

        if not all(
            [
                razorpay_payment_id,
                razorpay_order_id,
                razorpay_signature,
            ]
        ):
            return Response(
                {
                    "message": (
                        "razorpay_payment_id, "
                        "razorpay_order_id and "
                        "razorpay_signature are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            payment.razorpay_order_id
            != razorpay_order_id
        ):
            return Response(
                {
                    "message": (
                        "Razorpay order does not "
                        "match this booking."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.status == "SUCCESS":
            return Response(
                {
                    "message": "Payment is already verified.",
                    "booking_id":
                        str(booking.booking_id),
                    "booking_status":
                        booking.status,
                    "payment_status":
                        payment.status,
                },
                status=status.HTTP_200_OK,
            )

        if (
            not settings.RAZORPAY_KEY_ID
            or not settings.RAZORPAY_KEY_SECRET
        ):
            return Response(
                {
                    "message": (
                        "Razorpay credentials are not configured."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

        # ---------------------------------------------
        # VERIFY RAZORPAY SIGNATURE
        # ---------------------------------------------

        try:
            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id":
                        razorpay_order_id,
                    "razorpay_payment_id":
                        razorpay_payment_id,
                    "razorpay_signature":
                        razorpay_signature,
                }
            )

        except Exception:
            payment.status = "FAILED"

            payment.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            booking.payment_status = "FAILED"

            booking.save(
                update_fields=[
                    "payment_status",
                    "updated_at",
                ]
            )

            create_audit_log(
                request,
                "UPDATE",
                (
                    f"Payment verification failed for "
                    f"booking {booking.booking_id}."
                ),
            )

            return Response(
                {
                    "message": (
                        "Payment verification failed."
                    ),
                    "status": "FAILED",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------------------------
        # CHECK WHETHER HOLD IS STILL ACTIVE
        # ---------------------------------------------

        hold_active = (
            booking.status == "HELD"
            and booking.hold_expires_at is not None
            and booking.hold_expires_at > timezone.now()
        )

        # ---------------------------------------------
        # HOLD EXPIRED
        # ---------------------------------------------

        if not hold_active:

            try:
                razorpay_payment = client.payment.fetch(
                    razorpay_payment_id
                )

                razorpay_payment_status = (
                    razorpay_payment.get("status")
                )

            except Exception:
                return Response(
                    {
                        "message": (
                            "The booking window has expired "
                            "and the payment status could not "
                            "be confirmed with Razorpay."
                        ),
                        "status": "EXPIRED",
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            if razorpay_payment_status == "captured":

                try:
                    refund = client.payment.refund(
                        razorpay_payment_id,
                        {
                            "amount": int(
                                payment.amount * 100
                            )
                        },
                    )

                except Exception:
                    return Response(
                        {
                            "message": (
                                "Payment was received by "
                                "Razorpay, but the booking "
                                "window had expired and the "
                                "automatic refund could not "
                                "be processed."
                            ),
                            "refund_required": True,
                            "status": "EXPIRED",
                        },
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

                payment.razorpay_payment_id = (
                    razorpay_payment_id
                )

                payment.razorpay_signature = (
                    razorpay_signature
                )

                payment.refund_id = refund["id"]
                payment.status = "REFUNDED"

                payment.save()

                booking.status = "EXPIRED"
                booking.payment_status = "REFUNDED"
                booking.hold_expires_at = None

                booking.save()

                create_audit_log(
                    request,
                    "PAYMENT_REFUND",
                    (
                        f"Payment for booking "
                        f"{booking.booking_id} was refunded "
                        f"because the booking hold expired."
                    ),
                )

                return Response(
                    {
                        "message": (
                            "Payment was received after "
                            "the booking window expired. "
                            "The payment has been refunded."
                        ),
                        "booking_id":
                            str(booking.booking_id),
                        "booking_status":
                            booking.status,
                        "payment_status":
                            payment.status,
                        "refund_id":
                            payment.refund_id,
                        "refund_processed": True,
                    },
                    status=status.HTTP_200_OK,
                )

            payment.status = "FAILED"

            payment.razorpay_payment_id = (
                razorpay_payment_id
            )

            payment.razorpay_signature = (
                razorpay_signature
            )

            payment.save()

            booking.status = "EXPIRED"
            booking.payment_status = "FAILED"
            booking.hold_expires_at = None

            booking.save()

            create_audit_log(
                request,
                "UPDATE",
                (
                    f"Payment failed for expired booking "
                    f"{booking.booking_id}."
                ),
            )

            return Response(
                {
                    "message": (
                        "The booking window expired "
                        "before a successful payment."
                    ),
                    "booking_id":
                        str(booking.booking_id),
                    "booking_status":
                        booking.status,
                    "payment_status":
                        payment.status,
                    "refund_processed": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------------------------
        # SUCCESSFUL PAYMENT
        # ---------------------------------------------

        payment.razorpay_payment_id = (
            razorpay_payment_id
        )

        payment.razorpay_signature = (
            razorpay_signature
        )

        payment.status = "SUCCESS"

        payment.save()

        booking.status = "CONFIRMED"
        booking.payment_status = "SUCCESS"
        booking.hold_expires_at = None

        booking.save()

        create_audit_log(
            request,
            "PAYMENT_SUCCESS",
            (
                f"Payment of ₹{payment.amount} succeeded "
                f"for booking {booking.booking_id}."
            ),
        )

        # ---------------------------------------------
        # TRANSFER PAYMENT TO VENUE OWNER
        # ---------------------------------------------

        owner = VenueOwner.objects.filter(
            venues=booking.venue
        ).first()

        transfer_result = None
        transfer_error = None

        if owner:

            if owner.razorpay_account_id:

                try:
                    transfer_result = (
                        transfer_payment_to_owner(
                            razorpay_payment_id=(
                                payment.razorpay_payment_id
                            ),
                            razorpay_account_id=(
                                owner.razorpay_account_id
                            ),
                            amount=payment.amount,
                        )
                    )

                except Exception as exc:
                    transfer_error = str(exc)

            else:
                transfer_error = (
                    "Venue owner does not have "
                    "a Razorpay linked account."
                )

        else:
            transfer_error = (
                "Venue owner could not be found."
            )

        self.send_confirmation_email(booking)

        response_data = {
            "message": (
                "Payment verified and booking "
                "confirmed successfully."
            ),
            "booking_id":
                str(booking.booking_id),
            "booking_status":
                booking.status,
            "payment_status":
                payment.status,
            "owner_transfer_processed":
                transfer_result is not None,
        }

        if transfer_result is not None:
            response_data["owner_transfer"] = (
                transfer_result
            )

        if transfer_error:
            response_data["owner_transfer_error"] = (
                transfer_error
            )

        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )

    def send_confirmation_email(self, booking):

        email = booking.user.email

        if not email:
            return

        send_mail(
            subject="BookMyVenue Booking Confirmation",
            message=(
                "Your booking has been confirmed.\n\n"
                f"Booking ID: {booking.booking_id}\n"
                f"Venue: {booking.venue.venue_name}\n"
                f"Date: {booking.booking_date}\n"
                f"Time: {booking.start_time} - "
                f"{booking.end_time}\n"
                f"Amount: {booking.total_amount}\n"
            ),
            from_email=None,
            recipient_list=[email],
            fail_silently=True,
        )


class RefundPaymentView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, booking_id):

        booking = Booking.objects.select_for_update().filter(
            booking_id=booking_id,
            user=request.user,
        ).first()

        if booking is None:
            return Response(
                {"message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = self.process_refund(
            booking,
            request=request,
        )

        return Response(
            result["data"],
            status=result["status"],
        )

    @staticmethod
    def process_refund(
        booking,
        request=None,
    ):

        payment = Payment.objects.select_for_update().filter(
            booking=booking,
            user=booking.user,
        ).first()

        if payment is None:
            return {
                "status": status.HTTP_404_NOT_FOUND,
                "data": {
                    "message": "Payment not found.",
                },
            }

        if payment.status == "REFUNDED":
            return {
                "status": status.HTTP_200_OK,
                "data": {
                    "message":
                        "Payment has already been refunded.",
                    "booking_id":
                        str(booking.booking_id),
                    "refund_id":
                        payment.refund_id,
                    "payment_status":
                        "REFUNDED",
                    "refund_processed": True,
                },
            }

        if payment.status != "SUCCESS":
            return {
                "status": status.HTTP_400_BAD_REQUEST,
                "data": {
                    "message": (
                        "Only successful payments "
                        "can be refunded."
                    ),
                    "payment_status":
                        payment.status,
                    "refund_processed": False,
                },
            }

        if not payment.razorpay_payment_id:
            return {
                "status": status.HTTP_400_BAD_REQUEST,
                "data": {
                    "message": (
                        "No Razorpay payment ID is "
                        "available for this payment."
                    ),
                    "refund_processed": False,
                },
            }

        if (
            not settings.RAZORPAY_KEY_ID
            or not settings.RAZORPAY_KEY_SECRET
        ):
            return {
                "status":
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                "data": {
                    "message": (
                        "Razorpay credentials are "
                        "not configured."
                    ),
                    "refund_processed": False,
                },
            }

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

        try:
            refund = client.payment.refund(
                payment.razorpay_payment_id,
                {
                    "amount": int(
                        payment.amount * 100
                    ),
                },
            )

        except Exception:
            return {
                "status":
                    status.HTTP_502_BAD_GATEWAY,
                "data": {
                    "message": (
                        "Razorpay refund could not be "
                        "processed. The booking has "
                        "NOT been cancelled."
                    ),
                    "refund_processed": False,
                },
            }

        payment.refund_id = refund["id"]
        payment.status = "REFUNDED"

        payment.save()

        booking.payment_status = "REFUNDED"

        booking.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )

        if request is not None:
            create_audit_log(
                request,
                "PAYMENT_REFUND",
                (
                    f"Payment of ₹{payment.amount} was "
                    f"refunded for booking "
                    f"{booking.booking_id}."
                ),
            )

        return {
            "status": status.HTTP_200_OK,
            "data": {
                "message":
                    "Payment refunded successfully.",
                "booking_id":
                    str(booking.booking_id),
                "refund_id":
                    payment.refund_id,
                "payment_status":
                    payment.status,
                "refund_processed": True,
            },
        }