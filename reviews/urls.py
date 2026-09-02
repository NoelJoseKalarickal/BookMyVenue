from django.urls import path

from .views import (
    CreateReviewView,
    UpdateReviewView,
    DeleteReviewView,
    VenueReviewsView,
    ReplyToReviewView,
    ReportReviewView,
    AdminReportedReviewsView,
    AdminSuspendReviewView,
    AdminRestoreReviewView,
)


urlpatterns = [

    # Customer reviews
    path(
        "create/",
        CreateReviewView.as_view(),
        name="create-review",
    ),

    path(
        "<int:review_id>/update/",
        UpdateReviewView.as_view(),
        name="update-review",
    ),

    path(
        "<int:review_id>/delete/",
        DeleteReviewView.as_view(),
        name="delete-review",
    ),

    # Venue reviews
    path(
        "venue/<int:venue_id>/",
        VenueReviewsView.as_view(),
        name="venue-reviews",
    ),

    # Owner reply
    path(
        "<int:review_id>/reply/",
        ReplyToReviewView.as_view(),
        name="reply-review",
    ),

    # Reporting
    path(
        "<int:review_id>/report/",
        ReportReviewView.as_view(),
        name="report-review",
    ),

    # Admin moderation
    path(
        "admin/reported/",
        AdminReportedReviewsView.as_view(),
        name="admin-reported-reviews",
    ),

    path(
        "admin/<int:review_id>/suspend/",
        AdminSuspendReviewView.as_view(),
        name="admin-suspend-review",
    ),

    path(
        "admin/<int:review_id>/restore/",
        AdminRestoreReviewView.as_view(),
        name="admin-restore-review",
    ),
]