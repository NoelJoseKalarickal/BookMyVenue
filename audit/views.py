from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(APIView):

    permission_classes = [
        IsAdminUser
    ]

    def get(self, request):

        logs = AuditLog.objects.select_related(
            "user"
        ).order_by(
            "-created_at"
        )

        serializer = AuditLogSerializer(
            logs,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )