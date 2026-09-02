from datetime import datetime, timedelta

from django.core.mail import send_mail

from bookings.models import Booking

from audit.services import create_audit_log

from .models import Maintenance


ACTIVE_BOOKING_STATUSES = [
    "HELD",
    "CONFIRMED",
]


def maintenance_datetimes(maintenance):

    start = datetime.combine(
        maintenance.start_date,
        maintenance.start_time,
    )

    end = datetime.combine(
        maintenance.end_date,
        maintenance.end_time,
    )

    return start, end


def maintenance_overlaps_booking(
    maintenance,
    booking,
):

    maintenance_start, maintenance_end = (
        maintenance_datetimes(maintenance)
    )

    booking_start = datetime.combine(
        booking.booking_date,
        booking.start_time,
    )

    booking_end = datetime.combine(
        booking.booking_date,
        booking.end_time,
    )

    return (
        maintenance_start < booking_end
        and maintenance_end > booking_start
    )


def normal_maintenance_is_valid(
    maintenance,
):

    maintenance_start, maintenance_end = (
        maintenance_datetimes(maintenance)
    )

    bookings = Booking.objects.filter(
        venue=maintenance.venue,
        status__in=ACTIVE_BOOKING_STATUSES,
    )

    for booking in bookings:

        booking_start = datetime.combine(
            booking.booking_date,
            booking.start_time,
        )

        booking_end = datetime.combine(
            booking.booking_date,
            booking.end_time,
        )

        # Maintenance cannot overlap a booking.
        if (
            maintenance_start < booking_end
            and maintenance_end > booking_start
        ):
            return False, (
                "Normal maintenance cannot overlap "
                "an existing booking."
            )

        # Normal maintenance needs at least 1 hour
        # after an existing booking.
        if (
            booking_end <= maintenance_start
            and maintenance_start <
            booking_end + timedelta(hours=1)
        ):
            return False, (
                "Normal maintenance must start at least "
                "1 hour after the existing booking."
            )

    return True, None


def maintenance_blocks_booking(
    venue,
    booking_date,
    start_time,
    end_time,
):

    requested_start = datetime.combine(
        booking_date,
        start_time,
    )

    requested_end = datetime.combine(
        booking_date,
        end_time,
    )

    maintenances = Maintenance.objects.filter(
        venue=venue,
        status="APPROVED",
    )

    for maintenance in maintenances:

        maintenance_start, maintenance_end = (
            maintenance_datetimes(maintenance)
        )

        if (
            maintenance_start < requested_end
            and maintenance_end > requested_start
        ):
            return True

    return False


def get_current_maintenance(
    venue,
    target_date,
    target_time=None,
):

    maintenances = Maintenance.objects.filter(
        venue=venue,
        status="APPROVED",
        start_date__lte=target_date,
        end_date__gte=target_date,
    )

    for maintenance in maintenances:

        if target_date == maintenance.start_date:

            if (
                target_time is not None
                and target_time < maintenance.start_time
            ):
                continue

        if target_date == maintenance.end_date:

            if (
                target_time is not None
                and target_time >= maintenance.end_time
            ):
                continue

        return maintenance

    return None


def send_email(
    user,
    subject,
    message,
):

    if not user or not user.email:
        return

    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )


def notify_owner(
    maintenance,
    subject,
    message,
):

    send_email(
        maintenance.owner.user,
        subject,
        message,
    )


def notify_customer(
    booking,
    subject,
    message,
):

    send_email(
        booking.user,
        subject,
        message,
    )


def cancel_and_refund_emergency_bookings(
    maintenance,
    request=None,
):

    maintenance_start, maintenance_end = (
        maintenance_datetimes(maintenance)
    )

    affected_bookings = (
        Booking.objects
        .select_for_update()
        .filter(
            venue=maintenance.venue,
            status__in=ACTIVE_BOOKING_STATUSES,
        )
    )

    cancelled_bookings = []

    for booking in affected_bookings:

        booking_start = datetime.combine(
            booking.booking_date,
            booking.start_time,
        )

        booking_end = datetime.combine(
            booking.booking_date,
            booking.end_time,
        )

        overlaps = (
            maintenance_start < booking_end
            and maintenance_end > booking_start
        )

        if not overlaps:
            continue

        was_paid = (
            booking.payment_status == "SUCCESS"
        )

        # -----------------------------------------
        # REFUND PAID BOOKING
        # -----------------------------------------

        if was_paid:

            from payments.views import (
                RefundPaymentView
            )

            refund_result = (
                RefundPaymentView.process_refund(
                    booking,
                    request=request,
                )
            )

            if (
                refund_result["status"]
                != 200
            ):
                continue

            booking.payment_status = "REFUNDED"

        else:

            booking.payment_status = "FAILED"

        # -----------------------------------------
        # CANCEL BOOKING
        # -----------------------------------------

        booking.status = "CANCELLED"
        booking.hold_expires_at = None
        booking.queue_position = None

        booking.save()

        # -----------------------------------------
        # AUDIT LOG
        # -----------------------------------------

        if request is not None:

            create_audit_log(
                request,
                "BOOKING_CANCELLED",
                (
                    "Booking "
                    f"{booking.booking_id} was cancelled "
                    "because of emergency maintenance. "
                    f"Maintenance ID: {maintenance.id}. "
                    f"Venue: {maintenance.venue.venue_name}. "
                    f"Payment status: "
                    f"{booking.payment_status}"
                ),
            )

        # -----------------------------------------
        # CUSTOMER NOTIFICATION
        # -----------------------------------------

        if was_paid:

            notify_customer(
                booking,
                "BookMyVenue - Emergency Maintenance",
                (
                    "Your booking has been cancelled "
                    "because the venue requires emergency "
                    "maintenance.\n\n"
                    f"Booking ID: {booking.booking_id}\n"
                    f"Venue: {booking.venue.venue_name}\n"
                    f"Date: {booking.booking_date}\n"
                    f"Time: {booking.start_time} - "
                    f"{booking.end_time}\n\n"
                    "Your payment has been refunded."
                ),
            )

        else:

            notify_customer(
                booking,
                "BookMyVenue - Booking Cancelled",
                (
                    "Your booking has been cancelled "
                    "because the venue requires emergency "
                    "maintenance.\n\n"
                    f"Booking ID: {booking.booking_id}\n"
                    f"Venue: {booking.venue.venue_name}\n"
                    f"Date: {booking.booking_date}\n"
                    f"Time: {booking.start_time} - "
                    f"{booking.end_time}"
                ),
            )

        cancelled_bookings.append(
            booking.booking_id
        )

    return cancelled_bookings