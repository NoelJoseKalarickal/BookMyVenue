from rest_framework.permissions import BasePermission
from accounts.models import Customer


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and Customer.objects.filter(user=request.user).exists()
        )