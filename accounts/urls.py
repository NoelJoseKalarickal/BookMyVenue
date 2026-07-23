from django.urls import path
from .views import CustomerRegistrationView, VenueOwnerRegistrationView

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
]
