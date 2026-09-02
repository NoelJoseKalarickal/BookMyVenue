from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import VenueOwner
from venues.models import Venue

from audit.services import create_audit_log

from .models import Maintenance, MaintenanceImage

from .serializers import (
    MaintenanceSerializer,
    MaintenanceApprovalSerializer,
)

from .services import (
    normal_maintenance_is_valid,
    cancel_and_refund_emergency_bookings,
    notify_owner,
)


class CreateMaintenanceView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    @transaction.atomic
    def post(self, request):

        owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if owner is None:
            return Response(
                {
                    "message":
                        "Only venue owners can schedule maintenance."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        venue = Venue.objects.filter(
            id=request.data.get("venue"),
            venue_owner=owner,
        ).first()

        if venue is None:
            return Response(
                {
                    "message":
                        "Venue not found or you do not own this venue."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MaintenanceSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        maintenance_type = (
            serializer.validated_data[
                "maintenance_type"
            ]
        )

        maintenance = serializer.save(
            owner=owner,
            venue=venue,
            status=(
                "APPROVED"
                if maintenance_type == "NORMAL"
                else "PENDING"
            ),
        )

        # -----------------------------------------
        # NORMAL MAINTENANCE
        # -----------------------------------------

        if maintenance_type == "NORMAL":

            valid, message = (
                normal_maintenance_is_valid(
                    maintenance
                )
            )

            if not valid:

                maintenance.delete()

                return Response(
                    {
                        "message": message
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # -----------------------------------------
        # IMAGES
        # -----------------------------------------

        images = request.FILES.getlist(
            "images"
        )

        if maintenance_type == "EMERGENCY":

            if not images:

                maintenance.delete()

                return Response(
                    {
                        "message": (
                            "Emergency maintenance "
                            "requires at least one image."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        for image in images:

            MaintenanceImage.objects.create(
                maintenance=maintenance,
                image=image,
            )

        # -----------------------------------------
        # AUDIT LOG
        # -----------------------------------------

        if maintenance_type == "EMERGENCY":

            create_audit_log(
                request,
                "EMERGENCY_MAINTENANCE",
                (
                    "Emergency maintenance request "
                    f"submitted for venue "
                    f"'{venue.venue_name}'. "
                    f"Maintenance ID: {maintenance.id}. "
                    f"Date: {maintenance.start_date} to "
                    f"{maintenance.end_date}. "
                    f"Reason: {maintenance.reason}"
                ),
            )

        else:

            create_audit_log(
                request,
                "MAINTENANCE_CREATED",
                (
                    "Normal maintenance scheduled for venue "
                    f"'{venue.venue_name}'. "
                    f"Maintenance ID: {maintenance.id}. "
                    f"Date: {maintenance.start_date} to "
                    f"{maintenance.end_date}. "
                    f"Time: {maintenance.start_time} - "
                    f"{maintenance.end_time}. "
                    f"Reason: {maintenance.reason}"
                ),
            )

        # -----------------------------------------
        # OWNER NOTIFICATION
        # -----------------------------------------

        if maintenance_type == "EMERGENCY":

            notify_owner(
                maintenance,
                "Emergency Maintenance Submitted",
                (
                    "Your emergency maintenance request "
                    "has been submitted for admin approval.\n\n"
                    f"Venue: {venue.venue_name}\n"
                    f"Date: {maintenance.start_date} to "
                    f"{maintenance.end_date}\n"
                    f"Reason: {maintenance.reason}"
                ),
            )

            return Response(
                {
                    "message": (
                        "Emergency maintenance request "
                        "submitted for admin approval."
                    ),
                    "maintenance_id":
                        maintenance.id,
                    "status":
                        maintenance.status,
                },
                status=status.HTTP_201_CREATED,
            )

        notify_owner(
            maintenance,
            "Normal Maintenance Scheduled",
            (
                "Normal maintenance has been scheduled "
                "successfully.\n\n"
                f"Venue: {venue.venue_name}\n"
                f"Date: {maintenance.start_date} to "
                f"{maintenance.end_date}\n"
                f"Time: {maintenance.start_time} - "
                f"{maintenance.end_time}\n"
                f"Reason: {maintenance.reason}"
            ),
        )

        return Response(
            {
                "message":
                    "Normal maintenance scheduled successfully.",
                "maintenance_id":
                    maintenance.id,
                "status":
                    maintenance.status,
            },
            status=status.HTTP_201_CREATED,
        )


class MaintenanceListView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if owner:

            maintenances = Maintenance.objects.filter(
                owner=owner
            ).order_by(
                "start_date",
                "start_time",
            )

        elif request.user.is_staff:

            maintenances = Maintenance.objects.all().order_by(
                "status",
                "start_date",
                "start_time",
            )

        else:

            return Response(
                {
                    "message":
                        "Permission denied."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MaintenanceSerializer(
            maintenances,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class MaintenanceDetailView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(
        self,
        request,
        maintenance_id,
    ):

        maintenance = Maintenance.objects.filter(
            id=maintenance_id
        ).first()

        if maintenance is None:

            return Response(
                {
                    "message":
                        "Maintenance not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if (
            not request.user.is_staff
            and (
                owner is None
                or maintenance.owner != owner
            )
        ):

            return Response(
                {
                    "message":
                        "Permission denied."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MaintenanceSerializer(
            maintenance
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class ApproveMaintenanceView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    @transaction.atomic
    def post(
        self,
        request,
        maintenance_id,
    ):

        if not request.user.is_staff:

            return Response(
                {
                    "message":
                        "Only admins can approve emergency maintenance."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        maintenance = (
            Maintenance.objects
            .select_for_update()
            .filter(
                id=maintenance_id,
                maintenance_type="EMERGENCY",
                status="PENDING",
            )
            .first()
        )

        if maintenance is None:

            return Response(
                {
                    "message":
                        "Pending emergency maintenance request not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MaintenanceApprovalSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = serializer.validated_data[
            "action"
        ]

        admin_comment = (
            serializer.validated_data.get(
                "admin_comment",
                "",
            )
        )

        # -----------------------------------------
        # REJECT
        # -----------------------------------------

        if action == "REJECT":

            maintenance.status = "REJECTED"
            maintenance.admin_comment = admin_comment
            maintenance.approved_by = request.user
            maintenance.approved_at = timezone.now()

            maintenance.save()

            create_audit_log(
                request,
                "UPDATE",
                (
                    "Emergency maintenance request "
                    f"{maintenance.id} was rejected by admin. "
                    f"Venue: {maintenance.venue.venue_name}. "
                    f"Comment: {admin_comment}"
                ),
            )

            notify_owner(
                maintenance,
                "Emergency Maintenance Rejected",
                (
                    "Your emergency maintenance request "
                    "has been rejected by the admin.\n\n"
                    f"Venue: {maintenance.venue.venue_name}\n"
                    f"Reason: {admin_comment}"
                ),
            )

            return Response(
                {
                    "message":
                        "Emergency maintenance rejected.",
                    "status":
                        maintenance.status,
                },
                status=status.HTTP_200_OK,
            )

        # -----------------------------------------
        # APPROVE
        # -----------------------------------------

        maintenance.status = "APPROVED"
        maintenance.admin_comment = admin_comment
        maintenance.approved_by = request.user
        maintenance.approved_at = timezone.now()

        maintenance.save()

        create_audit_log(
            request,
            "EMERGENCY_MAINTENANCE",
            (
                "Emergency maintenance request "
                f"{maintenance.id} was approved by admin. "
                f"Venue: {maintenance.venue.venue_name}. "
                f"Date: {maintenance.start_date} to "
                f"{maintenance.end_date}. "
                f"Reason: {maintenance.reason}"
            ),
        )

        cancelled_bookings = (
            cancel_and_refund_emergency_bookings(
                maintenance,
                request=request,
            )
        )

        notify_owner(
            maintenance,
            "Emergency Maintenance Approved",
            (
                "Your emergency maintenance request "
                "has been approved by the admin.\n\n"
                f"Venue: {maintenance.venue.venue_name}\n"
                f"Date: {maintenance.start_date} to "
                f"{maintenance.end_date}\n"
                f"Time: {maintenance.start_time} - "
                f"{maintenance.end_time}\n"
                f"Cancelled bookings: "
                f"{len(cancelled_bookings)}"
            ),
        )

        return Response(
            {
                "message":
                    "Emergency maintenance approved.",
                "maintenance_id":
                    maintenance.id,
                "status":
                    maintenance.status,
                "cancelled_bookings": [
                    str(booking_id)
                    for booking_id
                    in cancelled_bookings
                ],
            },
            status=status.HTTP_200_OK,
        )


class CancelMaintenanceView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    @transaction.atomic
    def delete(
        self,
        request,
        maintenance_id,
    ):

        owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        maintenance = Maintenance.objects.filter(
            id=maintenance_id
        ).first()

        if maintenance is None:

            return Response(
                {
                    "message":
                        "Maintenance not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if (
            owner is None
            or maintenance.owner != owner
        ):

            return Response(
                {
                    "message":
                        "Permission denied."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if maintenance.status in [
            "CANCELLED",
            "COMPLETED",
        ]:

            return Response(
                {
                    "message":
                        "Maintenance cannot be cancelled."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        maintenance.status = "CANCELLED"

        maintenance.save()

        create_audit_log(
            request,
            "UPDATE",
            (
                "Maintenance "
                f"{maintenance.id} was cancelled. "
                f"Venue: {maintenance.venue.venue_name}. "
                f"Maintenance type: "
                f"{maintenance.maintenance_type}"
            ),
        )

        return Response(
            {
                "message":
                    "Maintenance cancelled successfully.",
                "status":
                    maintenance.status,
            },
            status=status.HTTP_200_OK,
        )