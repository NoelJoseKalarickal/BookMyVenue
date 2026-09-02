from datetime import datetime, timedelta
from decimal import Decimal

from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, BasePermission

from payments.views import RefundPaymentView

from venues.models import (
    Venue,
    WeeklySchedule,
    AvailabilityOverride,
)

from maintenance.services import (
    maintenance_blocks_booking,
)

from audit.services import create_audit_log

from accounts.models import VenueOwner

from .models import (
    Booking,
    PaidService,
    BookingService,
)


# ============================================================
# CREATE BOOKING
# ============================================================

class CreateBookingView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        venue_id = request.data.get("venue")
        booking_date = request.data.get("booking_date")
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")

        if not all([
            venue_id,
            booking_date,
            start_time,
            end_time,
        ]):
            return Response(
                {
                    "message": (
                        "venue, booking_date, start_time "
                        "and end_time are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        venue = Venue.objects.filter(
            id=venue_id
        ).first()

        if venue is None:
            return Response(
                {"message": "Venue not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            requested_date = datetime.strptime(
                booking_date,
                "%Y-%m-%d",
            ).date()

            requested_start = datetime.strptime(
                start_time,
                "%H:%M:%S",
            ).time()

            requested_end = datetime.strptime(
                end_time,
                "%H:%M:%S",
            ).time()

        except ValueError:
            return Response(
                {
                    "message": (
                        "Invalid date/time format. "
                        "Use YYYY-MM-DD and HH:MM:SS."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if requested_start >= requested_end:
            return Response(
                {
                    "message":
                        "Start time must be before end time."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.localtime()

        if requested_date < now.date():
            return Response(
                {"message": "Cannot book a past date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            requested_date == now.date()
            and requested_start <= now.time()
        ):
            return Response(
                {
                    "message": (
                        "This booking time has already "
                        "started or expired."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------------------------
        # MAINTENANCE CHECK
        # ---------------------------------------------

        if maintenance_blocks_booking(
            venue,
            requested_date,
            requested_start,
            requested_end,
        ):
            return Response(
                {
                    "message": (
                        "The venue is under maintenance "
                        "during the requested period. "
                        "Please select another time."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------------------------
        # EXPIRE HOLDS
        # ---------------------------------------------

        self.expire_holds(
            request,
            venue,
            requested_date,
            requested_start,
            requested_end,
        )

        # ---------------------------------------------
        # AVAILABILITY
        # ---------------------------------------------

        availability = self.get_availability(
            venue,
            requested_date,
        )

        if availability is None:
            return Response(
                {
                    "message": (
                        "Venue is not available "
                        "on this date."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        duration = (
            datetime.combine(
                requested_date,
                requested_end,
            )
            - datetime.combine(
                requested_date,
                requested_start,
            )
        )

        duration_minutes = int(
            duration.total_seconds() / 60
        )

        if duration_minutes < availability["minimum_duration"]:
            return Response(
                {
                    "message": (
                        "Booking duration is below "
                        "the minimum required duration."
                    ),
                    "minimum_booking_duration_minutes":
                        availability["minimum_duration"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not self.time_is_available(
            availability["slots"],
            requested_start,
            requested_end,
        ):
            return Response(
                {
                    "message": (
                        "Requested time is outside "
                        "the venue's availability."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------------------------
        # PAID SERVICES
        # ---------------------------------------------

        selected_services = request.data.get(
            "services",
            []
        )

        if selected_services is None:
            selected_services = []

        if not isinstance(selected_services, list):
            return Response(
                {
                    "message":
                        "services must be a list."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        service_objects = []
        service_total = Decimal("0")
        seen_service_ids = set()

        for item in selected_services:

            if not isinstance(item, dict):
                return Response(
                    {
                        "message": (
                            "Each service must contain "
                            "service_id and quantity."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            service_id = item.get("service_id")
            quantity = item.get("quantity")

            if not service_id:
                return Response(
                    {
                        "message":
                            "service_id is required."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                service_id = int(service_id)
            except (TypeError, ValueError):
                return Response(
                    {
                        "message":
                            "Invalid service_id."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if service_id in seen_service_ids:
                return Response(
                    {
                        "message": (
                            f"Service {service_id} "
                            "was selected more than once."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            seen_service_ids.add(service_id)

            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                return Response(
                    {
                        "message": (
                            f"Invalid quantity for "
                            f"service {service_id}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if quantity <= 0:
                return Response(
                    {
                        "message":
                            "Service quantity must be greater than 0."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            service = PaidService.objects.filter(
                id=service_id,
                venue=venue,
                is_active=True,
            ).first()

            if service is None:
                return Response(
                    {
                        "message": (
                            f"Service {service_id} is not "
                            "available for this venue."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            line_total = (
                service.price
                * Decimal(quantity)
            )

            service_total += line_total

            service_objects.append(
                {
                    "service": service,
                    "quantity": quantity,
                    "unit_price": service.price,
                    "total_price": line_total,
                }
            )

        # ---------------------------------------------
        # SAME USER OVERLAPPING BOOKING
        # ---------------------------------------------

        own_conflict = Booking.objects.select_for_update().filter(
            user=request.user,
            venue=venue,
            booking_date=requested_date,
            start_time__lt=requested_end,
            end_time__gt=requested_start,
            status__in=[
                "WAITING",
                "HELD",
                "CONFIRMED",
            ],
        ).first()

        if own_conflict:
            return Response(
                {
                    "message": (
                        "You already have an active booking "
                        "or queue entry for an overlapping time."
                    ),
                    "booking_id":
                        str(own_conflict.booking_id),
                    "status":
                        own_conflict.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------------------------
        # VENUE PRICE
        # ---------------------------------------------

        venue_total = (
            venue.price_per_hour
            * (
                Decimal(duration_minutes)
                / Decimal("60")
            )
        )

        total_amount = (
            venue_total
            + service_total
        )

        # ---------------------------------------------
        # CONFLICT + FCFS QUEUE
        # ---------------------------------------------

        conflict = self.find_conflict(
            request.user,
            venue,
            requested_date,
            requested_start,
            requested_end,
            availability["buffer"],
        )

        if conflict:

            waiting_count = Booking.objects.filter(
                venue=venue,
                booking_date=requested_date,
                status="WAITING",
                start_time__lt=requested_end,
                end_time__gt=requested_start,
            ).count()

            booking = Booking.objects.create(
                user=request.user,
                venue=venue,
                booking_date=requested_date,
                start_time=requested_start,
                end_time=requested_end,
                status="WAITING",
                queue_position=waiting_count + 1,
                payment_status="PENDING",
                total_amount=total_amount,
            )

            # Save selected services even while waiting.
            self.save_booking_services(
                booking,
                service_objects,
            )

            create_audit_log(
                request,
                "BOOKING_CREATED",
                (
                    f"Booking {booking.booking_id} created "
                    f"and added to the FCFS queue for "
                    f"venue '{venue.venue_name}'."
                ),
            )

            return Response(
                {
                    "message": (
                        "The requested period overlaps "
                        "with an active booking. "
                        "You have been added to the FCFS queue."
                    ),
                    "booking_id":
                        str(booking.booking_id),
                    "status":
                        booking.status,
                    "queue_position":
                        booking.queue_position,
                    "total_amount":
                        booking.total_amount,
                    "services":
                        self.get_booking_services_data(
                            booking
                        ),
                },
                status=status.HTTP_201_CREATED,
            )

        # ---------------------------------------------
        # FIRST USER GETS 5-MINUTE HOLD
        # ---------------------------------------------

        hold_expires = (
            timezone.now()
            + timedelta(minutes=5)
        )

        booking = Booking.objects.create(
            user=request.user,
            venue=venue,
            booking_date=requested_date,
            start_time=requested_start,
            end_time=requested_end,
            status="HELD",
            queue_position=1,
            hold_expires_at=hold_expires,
            payment_status="PENDING",
            total_amount=total_amount,
        )

        # Save selected paid services.
        self.save_booking_services(
            booking,
            service_objects,
        )

        create_audit_log(
            request,
            "BOOKING_CREATED",
            (
                f"Booking {booking.booking_id} created "
                f"and a 5-minute hold was placed for "
                f"venue '{venue.venue_name}'."
            ),
        )

        return Response(
            {
                "message": (
                    "Slot held for 5 minutes. "
                    "Create a Razorpay payment order "
                    "using this booking ID."
                ),
                "booking_id":
                    str(booking.booking_id),
                "status":
                    booking.status,
                "queue_position":
                    booking.queue_position,
                "hold_expires_at":
                    booking.hold_expires_at,
                "venue_amount":
                    venue_total,
                "services_amount":
                    service_total,
                "total_amount":
                    booking.total_amount,
                "services":
                    self.get_booking_services_data(
                        booking
                    ),
            },
            status=status.HTTP_201_CREATED,
        )

    # =============================================
    # SAVE BOOKING SERVICES
    # =============================================

    def save_booking_services(
        self,
        booking,
        service_objects,
    ):

        for selected in service_objects:

            service = selected["service"]

            BookingService.objects.create(
                booking=booking,
                service=service,
                service_name=service.name,
                unit_price=selected["unit_price"],
                quantity=selected["quantity"],
                total_price=selected["total_price"],
            )

    # =============================================
    # BOOKING SERVICES RESPONSE
    # =============================================

    def get_booking_services_data(
        self,
        booking,
    ):

        services = []

        for selected in booking.selected_services.all():

            services.append(
                {
                    "id":
                        selected.service.id
                        if selected.service
                        else None,
                    "name":
                        selected.service_name,
                    "unit_price":
                        str(selected.unit_price),
                    "quantity":
                        selected.quantity,
                    "total_price":
                        str(selected.total_price),
                }
            )

        return services

    # =============================================
    # AVAILABILITY
    # =============================================

    def get_availability(
        self,
        venue,
        requested_date,
    ):

        override = AvailabilityOverride.objects.filter(
            venue=venue,
            date=requested_date,
        ).first()

        if override:

            if override.status == "CLOSED":
                return None

            return {
                "minimum_duration":
                    override.minimum_booking_duration_minutes
                    or 60,
                "buffer":
                    override.buffer_time_minutes
                    or 0,
                "slots": [
                    (
                        override.start_time,
                        override.end_time,
                    )
                ],
            }

        day_name = requested_date.strftime(
            "%A"
        ).upper()

        schedule = WeeklySchedule.objects.filter(
            venue=venue,
            day_of_week=day_name,
            status="AVAILABLE",
        ).first()

        if schedule is None:
            return None

        slots = []
        minimum_duration = None
        buffer = 0

        for slot in schedule.time_slots.all():

            slots.append(
                (
                    slot.start_time,
                    slot.end_time,
                )
            )

            if minimum_duration is None:
                minimum_duration = (
                    slot.minimum_booking_duration_minutes
                )

            buffer = max(
                buffer,
                slot.buffer_time_minutes or 0,
            )

        return {
            "minimum_duration":
                minimum_duration or 60,
            "buffer":
                buffer,
            "slots":
                slots,
        }

    # =============================================
    # AVAILABILITY CHECK
    # =============================================

    def time_is_available(
        self,
        slots,
        requested_start,
        requested_end,
    ):

        for slot_start, slot_end in slots:

            if (
                requested_start >= slot_start
                and requested_end <= slot_end
            ):
                return True

        return False

    # =============================================
    # CONFLICT CHECK
    # =============================================

    def find_conflict(
        self,
        user,
        venue,
        booking_date,
        requested_start,
        requested_end,
        buffer_minutes,
    ):

        active_bookings = Booking.objects.select_for_update().filter(
            venue=venue,
            booking_date=booking_date,
            status__in=[
                "HELD",
                "CONFIRMED",
            ],
        )

        requested_start_dt = datetime.combine(
            booking_date,
            requested_start,
        )

        requested_end_dt = datetime.combine(
            booking_date,
            requested_end,
        )

        for booking in active_bookings:

            existing_start_dt = datetime.combine(
                booking_date,
                booking.start_time,
            )

            existing_end_dt = datetime.combine(
                booking_date,
                booking.end_time,
            )

            # Same user can book consecutive periods.
            if booking.user_id == user.id:

                if (
                    requested_start_dt
                    < existing_end_dt
                    and requested_end_dt
                    > existing_start_dt
                ):
                    return booking

                continue

            # Different users require the configured buffer.
            existing_start_with_buffer = (
                existing_start_dt
                - timedelta(minutes=buffer_minutes)
            )

            existing_end_with_buffer = (
                existing_end_dt
                + timedelta(minutes=buffer_minutes)
            )

            if (
                requested_start_dt
                < existing_end_with_buffer
                and requested_end_dt
                > existing_start_with_buffer
            ):
                return booking

        return None

    # =============================================
    # EXPIRE HOLDS
    # =============================================

    def expire_holds(
        self,
        request,
        venue,
        booking_date,
        start_time,
        end_time,
    ):

        expired = Booking.objects.select_for_update().filter(
            venue=venue,
            booking_date=booking_date,
            status="HELD",
            hold_expires_at__lte=timezone.now(),
            start_time__lt=end_time,
            end_time__gt=start_time,
        )

        for booking in expired:

            booking.status = "EXPIRED"
            booking.payment_status = "FAILED"
            booking.hold_expires_at = None

            booking.save()

            create_audit_log(
                request,
                "UPDATE",
                (
                    f"Booking {booking.booking_id} expired "
                    f"because its payment hold timed out."
                ),
            )

            self.promote_next_waiting(
                venue,
                booking_date,
                booking.start_time,
                booking.end_time,
            )

    # =============================================
    # PROMOTE NEXT WAITING USER
    # =============================================

    def promote_next_waiting(
        self,
        venue,
        booking_date,
        start_time,
        end_time,
    ):

        next_booking = Booking.objects.select_for_update().filter(
            venue=venue,
            booking_date=booking_date,
            status="WAITING",
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).order_by(
            "created_at"
        ).first()

        if next_booking is None:
            return

        next_booking.status = "HELD"
        next_booking.queue_position = 1
        next_booking.hold_expires_at = (
            timezone.now()
            + timedelta(minutes=5)
        )

        next_booking.save()

        waiting = Booking.objects.filter(
            venue=venue,
            booking_date=booking_date,
            status="WAITING",
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).order_by(
            "created_at"
        )

        position = 2

        for waiting_booking in waiting:

            waiting_booking.queue_position = position

            waiting_booking.save(
                update_fields=[
                    "queue_position",
                    "updated_at",
                ]
            )

            position += 1


# ============================================================
# CONFIRM BOOKING
# ============================================================

class ConfirmBookingView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):

        return Response(
            {
                "message": (
                    "Booking confirmation is handled "
                    "automatically after successful "
                    "Razorpay payment verification."
                ),
                "use_endpoint":
                    f"/payments/verify/{booking_id}/",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# CANCEL BOOKING
# ============================================================

class CancelBookingView(APIView):

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

        if booking.status not in [
            "HELD",
            "CONFIRMED",
        ]:
            return Response(
                {
                    "message": (
                        "Booking cannot be cancelled."
                    ),
                    "status":
                        booking.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        was_paid = (
            booking.payment_status == "SUCCESS"
        )

        # ---------------------------------------------
        # PAID BOOKING
        # ---------------------------------------------

        if was_paid:

            refund_result = (
                RefundPaymentView.process_refund(
                    booking
                )
            )

            if (
                refund_result["status"]
                != status.HTTP_200_OK
            ):
                return Response(
                    refund_result["data"],
                    status=refund_result["status"],
                )

        # ---------------------------------------------
        # CANCEL
        # ---------------------------------------------

        booking.status = "CANCELLED"
        booking.hold_expires_at = None

        if not was_paid:
            booking.payment_status = "FAILED"

        booking.save()

        create_audit_log(
            request,
            "BOOKING_CANCELLED",
            (
                f"Booking {booking.booking_id} for venue "
                f"'{booking.venue.venue_name}' was cancelled."
            ),
        )

        # ---------------------------------------------
        # PROMOTE NEXT FCFS USER
        # ---------------------------------------------

        next_booking = Booking.objects.select_for_update().filter(
            venue=booking.venue,
            booking_date=booking.booking_date,
            status="WAITING",
            start_time__lt=booking.end_time,
            end_time__gt=booking.start_time,
        ).order_by(
            "created_at"
        ).first()

        if next_booking:

            next_booking.status = "HELD"
            next_booking.queue_position = 1
            next_booking.hold_expires_at = (
                timezone.now()
                + timedelta(minutes=5)
            )

            next_booking.save()

            waiting_bookings = Booking.objects.filter(
                venue=booking.venue,
                booking_date=booking.booking_date,
                status="WAITING",
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time,
            ).order_by(
                "created_at"
            )

            position = 2

            for waiting_booking in waiting_bookings:

                waiting_booking.queue_position = position

                waiting_booking.save(
                    update_fields=[
                        "queue_position",
                        "updated_at",
                    ]
                )

                position += 1

        # ---------------------------------------------
        # CANCELLATION EMAIL
        # ---------------------------------------------

        self.send_cancellation_email(
            booking,
            was_paid,
        )

        return Response(
            {
                "message":
                    "Booking cancelled successfully.",
                "booking_id":
                    str(booking.booking_id),
                "status":
                    booking.status,
                "payment_status":
                    booking.payment_status,
                "refund_processed":
                    was_paid,
            },
            status=status.HTTP_200_OK,
        )

    def send_cancellation_email(
        self,
        booking,
        was_paid,
    ):

        email = booking.user.email

        if not email:
            return

        if was_paid:

            subject = (
                "BookMyVenue Booking Cancelled "
                "and Refund Processed"
            )

            message = (
                "Your BookMyVenue booking has been "
                "cancelled successfully.\n\n"
                f"Booking ID: {booking.booking_id}\n"
                f"Venue: {booking.venue.venue_name}\n"
                f"Date: {booking.booking_date}\n"
                f"Time: {booking.start_time} - "
                f"{booking.end_time}\n"
                f"Refund Status: Processed\n"
                f"Amount: {booking.total_amount}\n"
            )

        else:

            subject = (
                "BookMyVenue Booking Cancelled"
            )

            message = (
                "Your BookMyVenue booking has been "
                "cancelled successfully.\n\n"
                f"Booking ID: {booking.booking_id}\n"
                f"Venue: {booking.venue.venue_name}\n"
                f"Date: {booking.booking_date}\n"
                f"Time: {booking.start_time} - "
                f"{booking.end_time}\n"
            )

        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[email],
            fail_silently=True,
        )


# ============================================================
# PROCESS EXPIRED BOOKINGS
# ============================================================

class ProcessExpiredBookingsView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        now = timezone.now()

        expired_bookings = Booking.objects.select_for_update().filter(
            status="HELD",
            hold_expires_at__lte=now,
        )

        promoted = []

        for booking in expired_bookings:

            booking.status = "EXPIRED"
            booking.payment_status = "FAILED"
            booking.hold_expires_at = None

            booking.save()

            create_audit_log(
                request,
                "UPDATE",
                (
                    f"Booking {booking.booking_id} expired "
                    f"because its payment hold timed out."
                ),
            )

            next_booking = Booking.objects.select_for_update().filter(
                venue=booking.venue,
                booking_date=booking.booking_date,
                status="WAITING",
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time,
            ).order_by(
                "created_at"
            ).first()

            if next_booking:

                next_booking.status = "HELD"
                next_booking.queue_position = 1
                next_booking.hold_expires_at = (
                    timezone.now()
                    + timedelta(minutes=5)
                )

                next_booking.save()

                waiting_bookings = Booking.objects.filter(
                    venue=booking.venue,
                    booking_date=booking.booking_date,
                    status="WAITING",
                    start_time__lt=booking.end_time,
                    end_time__gt=booking.start_time,
                ).order_by(
                    "created_at"
                )

                position = 2

                for waiting_booking in waiting_bookings:

                    waiting_booking.queue_position = position

                    waiting_booking.save(
                        update_fields=[
                            "queue_position",
                            "updated_at",
                        ]
                    )

                    position += 1

                promoted.append(
                    {
                        "expired_booking_id":
                            str(booking.booking_id),
                        "new_held_booking_id":
                            str(next_booking.booking_id),
                    }
                )

        return Response(
            {
                "message":
                    "Expired bookings processed.",
                "promoted":
                    promoted,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# BOOKING DETAIL
# ============================================================

class BookingDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):

        booking = Booking.objects.filter(
            booking_id=booking_id,
            user=request.user,
        ).first()

        if booking is None:
            return Response(
                {"message": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        services = []

        for selected in booking.selected_services.all():

            services.append(
                {
                    "id":
                        selected.service.id
                        if selected.service
                        else None,
                    "name":
                        selected.service_name,
                    "unit_price":
                        str(selected.unit_price),
                    "quantity":
                        selected.quantity,
                    "total_price":
                        str(selected.total_price),
                }
            )

        return Response(
            {
                "booking_id":
                    str(booking.booking_id),
                "venue":
                    booking.venue.id,
                "venue_name":
                    booking.venue.venue_name,
                "booking_date":
                    booking.booking_date,
                "start_time":
                    booking.start_time,
                "end_time":
                    booking.end_time,
                "status":
                    booking.status,
                "queue_position":
                    booking.queue_position,
                "hold_expires_at":
                    booking.hold_expires_at,
                "payment_status":
                    booking.payment_status,
                "total_amount":
                    booking.total_amount,
                "services":
                    services,
                "created_at":
                    booking.created_at,
                "updated_at":
                    booking.updated_at,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# MY BOOKINGS
# ============================================================

class MyBookingsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        bookings = Booking.objects.filter(
            user=request.user
        ).prefetch_related(
            "selected_services"
        ).order_by(
            "-created_at"
        )

        data = []

        for booking in bookings:

            services = []

            for selected in booking.selected_services.all():

                services.append(
                    {
                        "id":
                            selected.service.id
                            if selected.service
                            else None,
                        "name":
                            selected.service_name,
                        "unit_price":
                            str(selected.unit_price),
                        "quantity":
                            selected.quantity,
                        "total_price":
                            str(selected.total_price),
                    }
                )

            data.append(
                {
                    "booking_id":
                        str(booking.booking_id),
                    "venue":
                        booking.venue.id,
                    "venue_name":
                        booking.venue.venue_name,
                    "booking_date":
                        booking.booking_date,
                    "start_time":
                        booking.start_time,
                    "end_time":
                        booking.end_time,
                    "status":
                        booking.status,
                    "queue_position":
                        booking.queue_position,
                    "hold_expires_at":
                        booking.hold_expires_at,
                    "payment_status":
                        booking.payment_status,
                    "total_amount":
                        booking.total_amount,
                    "services":
                        services,
                    "created_at":
                        booking.created_at,
                    "updated_at":
                        booking.updated_at,
                }
            )

        return Response(
            data,
            status=status.HTTP_200_OK,
        )


# ============================================================
# OWNER PERMISSION
# ============================================================

class IsVenueOwnerUser(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and VenueOwner.objects.filter(
                user=request.user
            ).exists()
        )


# ============================================================
# CUSTOMER - VIEW VENUE SERVICES
# ============================================================

class VenuePaidServiceListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, venue_id):

        venue = Venue.objects.filter(
            id=venue_id
        ).first()

        if venue is None:
            return Response(
                {
                    "message":
                        "Venue not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        services = PaidService.objects.filter(
            venue=venue,
            is_active=True,
        ).order_by(
            "name"
        )

        data = []

        for service in services:

            data.append(
                {
                    "id":
                        service.id,
                    "venue":
                        service.venue_id,
                    "name":
                        service.name,
                    "description":
                        service.description,
                    "price":
                        str(service.price),
                    "is_active":
                        service.is_active,
                }
            )

        return Response(
            {
                "venue_id":
                    venue.id,
                "venue_name":
                    venue.venue_name,
                "services":
                    data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# OWNER - LIST / CREATE SERVICES
# ============================================================

class OwnerPaidServiceListCreateView(APIView):

    permission_classes = [IsVenueOwnerUser]

    def get(self, request):

        owner = VenueOwner.objects.get(
            user=request.user
        )

        services = PaidService.objects.filter(
            venue__venue_owner=owner
        ).select_related(
            "venue"
        ).order_by(
            "venue__venue_name",
            "name",
        )

        data = []

        for service in services:

            data.append(
                {
                    "id":
                        service.id,
                    "venue":
                        service.venue_id,
                    "venue_name":
                        service.venue.venue_name,
                    "name":
                        service.name,
                    "description":
                        service.description,
                    "price":
                        str(service.price),
                    "is_active":
                        service.is_active,
                }
            )

        return Response(
            data,
            status=status.HTTP_200_OK,
        )

    def post(self, request):

        owner = VenueOwner.objects.get(
            user=request.user
        )

        venue_id = request.data.get(
            "venue"
        )

        name = request.data.get(
            "name"
        )

        description = request.data.get(
            "description",
            "",
        )

        price = request.data.get(
            "price"
        )

        if not venue_id:
            return Response(
                {
                    "message":
                        "Venue is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not name:
            return Response(
                {
                    "message":
                        "Service name is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if price is None:
            return Response(
                {
                    "message":
                        "Service price is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            price = Decimal(
                str(price)
            )
        except Exception:
            return Response(
                {
                    "message":
                        "Invalid service price."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if price < 0:
            return Response(
                {
                    "message":
                        "Service price cannot be negative."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        venue = get_object_or_404(
            Venue,
            id=venue_id,
            venue_owner=owner,
        )

        service = PaidService.objects.create(
            venue=venue,
            name=name,
            description=description,
            price=price,
            is_active=True,
        )

        create_audit_log(
            request,
            "CREATE",
            (
                f"Paid service '{service.name}' "
                f"created for venue "
                f"'{venue.venue_name}'."
            ),
        )

        return Response(
            {
                "message":
                    "Paid service created successfully.",
                "service":
                    {
                        "id":
                            service.id,
                        "venue":
                            venue.id,
                        "name":
                            service.name,
                        "description":
                            service.description,
                        "price":
                            str(service.price),
                        "is_active":
                            service.is_active,
                    },
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# OWNER - UPDATE / DELETE SERVICE
# ============================================================

class OwnerPaidServiceDetailView(APIView):

    permission_classes = [IsVenueOwnerUser]

    def patch(self, request, service_id):

        owner = VenueOwner.objects.get(
            user=request.user
        )

        service = get_object_or_404(
            PaidService,
            id=service_id,
            venue__venue_owner=owner,
        )

        if "name" in request.data:

            name = request.data.get(
                "name"
            )

            if not name:
                return Response(
                    {
                        "message":
                            "Service name cannot be empty."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            service.name = name

        if "description" in request.data:

            service.description = request.data.get(
                "description",
                "",
            )

        if "price" in request.data:

            try:
                price = Decimal(
                    str(
                        request.data.get(
                            "price"
                        )
                    )
                )
            except Exception:
                return Response(
                    {
                        "message":
                            "Invalid service price."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if price < 0:
                return Response(
                    {
                        "message":
                            "Service price cannot be negative."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            service.price = price

        if "is_active" in request.data:

            value = request.data.get(
                "is_active"
            )

            if isinstance(value, bool):
                service.is_active = value

            elif str(value).lower() == "true":
                service.is_active = True

            elif str(value).lower() == "false":
                service.is_active = False

            else:
                return Response(
                    {
                        "message":
                            "is_active must be true or false."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        service.save()

        create_audit_log(
            request,
            "UPDATE",
            (
                f"Paid service '{service.name}' "
                f"updated."
            ),
        )

        return Response(
            {
                "message":
                    "Paid service updated successfully.",
                "service":
                    {
                        "id":
                            service.id,
                        "venue":
                            service.venue_id,
                        "name":
                            service.name,
                        "description":
                            service.description,
                        "price":
                            str(service.price),
                        "is_active":
                            service.is_active,
                    },
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, service_id):

        owner = VenueOwner.objects.get(
            user=request.user
        )

        service = get_object_or_404(
            PaidService,
            id=service_id,
            venue__venue_owner=owner,
        )

        # Deactivate instead of physically deleting.
        # Existing bookings retain their price snapshot.
        service.is_active = False

        service.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        create_audit_log(
            request,
            "DELETE",
            (
                f"Paid service '{service.name}' "
                f"was deactivated."
            ),
        )

        return Response(
            {
                "message":
                    "Paid service deactivated successfully."
            },
            status=status.HTTP_200_OK,
        )