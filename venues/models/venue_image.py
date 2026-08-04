from django.db import models

from .venue import Venue


def venue_image_path(instance, filename):
    return f"venue_images/venue_{instance.venue.id}/{filename}"


class VenueImage(models.Model):
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to=venue_image_path
    )

    is_primary = models.BooleanField(
        default=False
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["venue", "image"],
                name="unique_image_per_venue"
            )
        ]

    def delete(self, *args, **kwargs):
        self.image.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.venue.venue_name} - Image {self.id}"