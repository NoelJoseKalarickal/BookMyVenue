from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from venues.models import EventType
from venues.serializers import EventTypeSerializer


class EventTypeListView(APIView):
    def get(self, request):
        event_types = EventType.objects.all()

        serializer = EventTypeSerializer(event_types, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)