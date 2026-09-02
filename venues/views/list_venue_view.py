from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from venues.models.venue import Venue
from venues.serializers.venue_list_serializer import VenueListSerializer
from venues.permissions import IsCustomer


class VenueListView(ListAPIView):
    serializer_class = VenueListSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def get_queryset(self):
        queryset = Venue.objects.filter(
            is_active=True,
            is_approved=True
        )

        # -----------------------------------------
        # 1. GENERAL SEARCH
        # -----------------------------------------
        # Example:
        # /api/venues/?search=grand
        #
        # Searches venue name OR location
        search = self.request.query_params.get("search")

        if search:
            queryset = queryset.filter(
                Q(venue_name__icontains=search) |
                Q(location__icontains=search)
            )

        # -----------------------------------------
        # 2. VENUE NAME
        # -----------------------------------------
        # Example:
        # /api/venues/?venue_name=Grand Palace
        venue_name = self.request.query_params.get("venue_name")

        if venue_name:
            queryset = queryset.filter(
                venue_name__icontains=venue_name
            )

        # -----------------------------------------
        # 3. LOCATION
        # -----------------------------------------
        # Example:
        # /api/venues/?location=Kochi
        location = self.request.query_params.get("location")

        if location:
            queryset = queryset.filter(
                location__icontains=location
            )

        # -----------------------------------------
        # 4. EVENT TYPE
        # -----------------------------------------
        # Example:
        # /api/venues/?event_type=Wedding
        event_type = self.request.query_params.get("event_type")

        if event_type:
            queryset = queryset.filter(
                event_types__name__icontains=event_type
            )

        # -----------------------------------------
        # 5. MINIMUM CAPACITY
        # -----------------------------------------
        # Example:
        # /api/venues/?min_capacity=200
        min_capacity = self.request.query_params.get("min_capacity")

        if min_capacity:
            try:
                queryset = queryset.filter(
                    capacity__gte=int(min_capacity)
                )
            except ValueError:
                pass

        # -----------------------------------------
        # 6. MAXIMUM CAPACITY
        # -----------------------------------------
        # Example:
        # /api/venues/?max_capacity=500
        max_capacity = self.request.query_params.get("max_capacity")

        if max_capacity:
            try:
                queryset = queryset.filter(
                    capacity__lte=int(max_capacity)
                )
            except ValueError:
                pass

        # -----------------------------------------
        # 7. MINIMUM PRICE
        # -----------------------------------------
        # Example:
        # /api/venues/?min_price=2000
        min_price = self.request.query_params.get("min_price")

        if min_price:
            try:
                queryset = queryset.filter(
                    price_per_hour__gte=min_price
                )
            except ValueError:
                pass

        # -----------------------------------------
        # 8. MAXIMUM PRICE
        # -----------------------------------------
        # Example:
        # /api/venues/?max_price=5000
        max_price = self.request.query_params.get("max_price")

        if max_price:
            try:
                queryset = queryset.filter(
                    price_per_hour__lte=max_price
                )
            except ValueError:
                pass

        # -----------------------------------------
        # 9. MINIMUM RATING
        # -----------------------------------------
        # Example:
        # /api/venues/?min_rating=4
        min_rating = self.request.query_params.get("min_rating")

        if min_rating:
            try:
                queryset = queryset.filter(
                    average_rating__gte=min_rating
                )
            except ValueError:
                pass

        # -----------------------------------------
        # 10. SORTING
        # -----------------------------------------
        # Examples:
        #
        # ?sort=price_low
        # ?sort=price_high
        # ?sort=rating_high
        # ?sort=rating_low
        sort = self.request.query_params.get("sort")

        if sort == "price_low":
            queryset = queryset.order_by("price_per_hour")

        elif sort == "price_high":
            queryset = queryset.order_by("-price_per_hour")

        elif sort == "rating_high":
            queryset = queryset.order_by("-average_rating")

        elif sort == "rating_low":
            queryset = queryset.order_by("average_rating")

        # Prevent duplicate venues when filtering
        # through the ManyToMany event_types relationship.
        return queryset.distinct()