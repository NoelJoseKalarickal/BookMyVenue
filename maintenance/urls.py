from django.urls import path

from .views import (
    CreateMaintenanceView,
    MaintenanceListView,
    MaintenanceDetailView,
    ApproveMaintenanceView,
    CancelMaintenanceView,
)


urlpatterns = [

    path(
        "create/",
        CreateMaintenanceView.as_view(),
        name="create-maintenance",
    ),

    path(
        "my/",
        MaintenanceListView.as_view(),
        name="maintenance-list",
    ),

    path(
        "<int:maintenance_id>/",
        MaintenanceDetailView.as_view(),
        name="maintenance-detail",
    ),

    path(
        "<int:maintenance_id>/approve/",
        ApproveMaintenanceView.as_view(),
        name="approve-maintenance",
    ),

    path(
        "<int:maintenance_id>/cancel/",
        CancelMaintenanceView.as_view(),
        name="cancel-maintenance",
    ),
]