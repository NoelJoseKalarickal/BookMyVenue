from .models import AuditLog


def get_client_ip(request):
    """
    Get the client's IP address.
    """

    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR"
    )

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get(
        "REMOTE_ADDR"
    )


def create_audit_log(
    request,
    action,
    description,
):
    """
    Create an audit log entry.
    """

    user = (
        request.user
        if request.user.is_authenticated
        else None
    )

    return AuditLog.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=get_client_ip(request),
    )