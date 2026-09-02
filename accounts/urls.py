from django.urls import path

from .views import (
    CustomerRegistrationView,
    VenueOwnerRegistrationView,
    VerifyOTPView,
    CreateRazorpayLinkedAccountView,
    CreateRazorpayStakeholderView,
    RequestRazorpayRouteProductView,
    UpdateRazorpayBankDetailsView,
)


urlpatterns = [

    # Existing registration
    path(
        "customer/register/",
        CustomerRegistrationView.as_view(),
        name="customer-register",
    ),

    path(
        "venue-owner/register/",
        VenueOwnerRegistrationView.as_view(),
        name="venue-owner-register",
    ),

    path(
        "verify-otp/",
        VerifyOTPView.as_view(),
        name="verify-otp",
    ),

    # Razorpay Route
    path(
        "razorpay/create-account/",
        CreateRazorpayLinkedAccountView.as_view(),
        name="create-razorpay-linked-account",
    ),

    path(
        "razorpay/create-stakeholder/",
        CreateRazorpayStakeholderView.as_view(),
        name="create-razorpay-stakeholder",
    ),

    path(
        "razorpay/request-product/",
        RequestRazorpayRouteProductView.as_view(),
        name="request-razorpay-route-product",
    ),

    path(
        "razorpay/bank-details/",
        UpdateRazorpayBankDetailsView.as_view(),
        name="update-razorpay-bank-details",
    ),
]