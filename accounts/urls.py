from django.urls import path
from .views import (
    CustomerRegistrationView,
    VenueOwnerRegistrationView,
    OTPVerificationView,
)

urlpatterns = [
    path(
        "register/customer/",
        CustomerRegistrationView.as_view(),
        name="customer-register",
    ),
    path(
        "register/owner/",
        VenueOwnerRegistrationView.as_view(),
        name="owner-register",
    ),
    path(
        "verify-otp/",
        OTPVerificationView.as_view(),
        name="verify-otp",
    ),
]
