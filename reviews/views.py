from datetime import datetime

from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import (
    IsAuthenticated,
    IsAdminUser,
)

from bookings.models import Booking
from accounts.models import Customer, VenueOwner

from .models import Review
from .serializers import (
    ReviewSerializer,
    CreateReviewSerializer,
    UpdateReviewSerializer,
    OwnerReplySerializer,
    ReportReviewSerializer,
)
from .services import update_venue_rating


def booking_has_finished(booking):
    """
    Returns True only when the customer's
    actual booking period has completely ended.
    """

    booking_end = datetime.combine(
        booking.booking_date,
        booking.end_time,
    )

    booking_end = timezone.make_aware(
        booking_end,
        timezone.get_current_timezone(),
    )

    return timezone.now() >= booking_end


class CreateReviewView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(self, request):

        # Customer check
        customer = Customer.objects.filter(
            user=request.user
        ).first()

        if customer is None:
            return Response(
                {
                    "message":
                    "Only customers can submit reviews."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CreateReviewSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the Booking object directly from the serializer.
        # This works whether Booking uses id or booking_id
        # as its primary key.
        booking = serializer.validated_data["booking"]

        # Booking must belong to logged-in customer
        if booking.user != request.user:
            return Response(
                {
                    "message":
                    "You can only review a venue you booked."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Booking must be confirmed
        if booking.status != "CONFIRMED":
            return Response(
                {
                    "message":
                    "Only confirmed bookings can be reviewed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Booking must have finished
        if not booking_has_finished(booking):
            return Response(
                {
                    "message":
                    "You can review the venue only after "
                    "your booking has ended."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # One review per booking
        if Review.objects.filter(
            booking=booking
        ).exists():

            return Response(
                {
                    "message":
                    "You have already reviewed this booking."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        review = serializer.save(
            customer=request.user,
            venue=booking.venue,
        )

        update_venue_rating(
            booking.venue
        )

        return Response(
            {
                "message":
                "Review submitted successfully.",
                "review":
                ReviewSerializer(review).data,
            },
            status=status.HTTP_201_CREATED,
        )


class UpdateReviewView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def put(self, request, review_id):

        review = get_object_or_404(
            Review,
            id=review_id,
        )

        if review.customer != request.user:
            return Response(
                {
                    "message":
                    "You can only edit your own review."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if review.status == "SUSPENDED":
            return Response(
                {
                    "message":
                    "Suspended reviews cannot be edited."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UpdateReviewSerializer(
            review,
            data=request.data,
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()

        update_venue_rating(
            review.venue
        )

        return Response(
            {
                "message":
                "Review updated successfully.",
                "review":
                ReviewSerializer(review).data,
            },
            status=status.HTTP_200_OK,
        )


class DeleteReviewView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def delete(self, request, review_id):

        review = get_object_or_404(
            Review,
            id=review_id,
        )

        if review.customer != request.user:
            return Response(
                {
                    "message":
                    "You can only delete your own review."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        venue = review.venue

        review.delete()

        update_venue_rating(venue)

        return Response(
            {
                "message":
                "Review deleted successfully."
            },
            status=status.HTTP_200_OK,
        )


class VenueReviewsView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request, venue_id):

        reviews = Review.objects.filter(
            venue_id=venue_id,
            status="ACTIVE",
        ).order_by(
            "-created_at"
        )

        serializer = ReviewSerializer(
            reviews,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class ReplyToReviewView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(self, request, review_id):

        review = get_object_or_404(
            Review,
            id=review_id,
        )

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {
                    "message":
                    "Only venue owners can reply to reviews."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check that owner owns the venue
        if review.venue.venue_owner != venue_owner:
            return Response(
                {
                    "message":
                    "You can only reply to reviews "
                    "for your own venues."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if review.status == "SUSPENDED":
            return Response(
                {
                    "message":
                    "Suspended reviews cannot receive replies."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OwnerReplySerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        review.owner_reply = serializer.validated_data[
            "reply"
        ]

        review.save(
            update_fields=[
                "owner_reply",
                "updated_at",
            ]
        )

        return Response(
            {
                "message":
                "Reply added successfully.",
                "review":
                ReviewSerializer(review).data,
            },
            status=status.HTTP_200_OK,
        )


class ReportReviewView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(self, request, review_id):

        customer = Customer.objects.filter(
            user=request.user
        ).first()

        if customer is None:
            return Response(
                {
                    "message":
                    "Only customers can report reviews."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        review = get_object_or_404(
            Review,
            id=review_id,
        )

        if review.customer == request.user:
            return Response(
                {
                    "message":
                    "You cannot report your own review."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if review.status == "SUSPENDED":
            return Response(
                {
                    "message":
                    "This review is already suspended."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReportReviewSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        review.status = "REPORTED"
        review.report_reason = (
            serializer.validated_data["reason"]
        )
        review.reported_at = timezone.now()

        review.save(
            update_fields=[
                "status",
                "report_reason",
                "reported_at",
                "updated_at",
            ]
        )

        return Response(
            {
                "message":
                "Review reported successfully."
            },
            status=status.HTTP_200_OK,
        )


class AdminReportedReviewsView(APIView):

    permission_classes = [
        IsAdminUser
    ]

    def get(self, request):

        reviews = Review.objects.filter(
            status="REPORTED"
        ).order_by(
            "-reported_at"
        )

        serializer = ReviewSerializer(
            reviews,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class AdminSuspendReviewView(APIView):

    permission_classes = [
        IsAdminUser
    ]

    def post(self, request, review_id):

        review = get_object_or_404(
            Review,
            id=review_id,
        )

        review.status = "SUSPENDED"
        review.suspended_at = timezone.now()

        review.save(
            update_fields=[
                "status",
                "suspended_at",
                "updated_at",
            ]
        )

        update_venue_rating(
            review.venue
        )

        return Response(
            {
                "message":
                "Review suspended successfully."
            },
            status=status.HTTP_200_OK,
        )


class AdminRestoreReviewView(APIView):

    permission_classes = [
        IsAdminUser
    ]

    def post(self, request, review_id):

        review = get_object_or_404(
            Review,
            id=review_id,
        )

        review.status = "ACTIVE"
        review.report_reason = None
        review.reported_at = None
        review.suspended_at = None

        review.save(
            update_fields=[
                "status",
                "report_reason",
                "reported_at",
                "suspended_at",
                "updated_at",
            ]
        )

        update_venue_rating(
            review.venue
        )

        return Response(
            {
                "message":
                "Review restored successfully."
            },
            status=status.HTTP_200_OK,
        )