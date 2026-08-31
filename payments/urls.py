from django.urls import path

from .views import (
    CreatePaymentOrderView,
    VerifyPaymentView,
    RefundPaymentView,
)


urlpatterns = [

    path(
        "create/<uuid:booking_id>/",
        CreatePaymentOrderView.as_view(),
        name="create-payment-order",
    ),

    path(
        "verify/<uuid:booking_id>/",
        VerifyPaymentView.as_view(),
        name="verify-payment",
    ),

    path(
        "refund/<uuid:booking_id>/",
        RefundPaymentView.as_view(),
        name="refund-payment",
    ),

]