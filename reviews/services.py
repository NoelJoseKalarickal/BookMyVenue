from django.db.models import Avg

from .models import Review


def update_venue_rating(venue):
    reviews = Review.objects.filter(
        venue=venue,
        status="ACTIVE",
    )

    total_reviews = reviews.count()

    if total_reviews == 0:
        venue.average_rating = 0
        venue.total_reviews = 0

    else:
        average = reviews.aggregate(
            average=Avg("rating")
        )["average"]

        venue.average_rating = round(
            float(average),
            2,
        )

        venue.total_reviews = total_reviews

    venue.save(
        update_fields=[
            "average_rating",
            "total_reviews",
        ]
    )