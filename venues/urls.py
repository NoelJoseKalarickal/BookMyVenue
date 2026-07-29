from django.urls import path
from .views import AddVenueView

urlpatterns = [
    path("add/", AddVenueView.as_view(), name="add-venue"),
]