from django.contrib import admin

from .models import (
    Maintenance,
    MaintenanceImage,
)


class MaintenanceImageInline(
    admin.TabularInline
):

    model = MaintenanceImage
    extra = 0


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "venue",
        "owner",
        "maintenance_type",
        "status",
        "start_date",
        "start_time",
        "end_date",
        "end_time",
        "created_at",
    )

    list_filter = (
        "maintenance_type",
        "status",
        "start_date",
    )

    search_fields = (
        "venue__venue_name",
        "owner__name",
        "reason",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "approved_at",
    )

    inlines = [
        MaintenanceImageInline,
    ]