from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from incidents.access import incidents_for_user
from .models import Notification
from .serializers import NotificationRecordSerializer, NotificationSerializer
from .services import retry_failed


class NotificationListView(generics.ListAPIView):
    """GET /api/notifications/ - notifications addressed to me."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_read', 'channel', 'delivery_status']

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class NotificationDetailView(generics.RetrieveAPIView):
    """GET /api/notifications/<id>/ - 404 if it is not addressed to me."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class NotificationReadView(APIView):
    """PATCH /api/notifications/<id>/read/ - read status only; delivery status is untouched."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        note = get_object_or_404(Notification, pk=pk, recipient=request.user)
        if note.channel != 'in_app':
            return Response(
                {'detail': 'Only in-app notifications can be marked as read.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not note.is_read:
            note.is_read = True
            note.read_at = timezone.now()
            note.save(update_fields=['is_read', 'read_at'])
        return Response(NotificationSerializer(note).data)


class IncidentNotificationListView(generics.ListAPIView):
    """GET /api/incidents/<id>/notifications/ - delivery records for monitoring."""
    serializer_class = NotificationRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['delivery_status', 'channel', 'recipient_type']

    def get_queryset(self):
        user = self.request.user
        if user.role in ('guardian', 'volunteer'):
            raise PermissionDenied('You cannot view notification records for this incident.')
        incident = get_object_or_404(incidents_for_user(user), pk=self.kwargs['pk'])
        return Notification.objects.filter(incident=incident)


class IncidentNotificationRetryView(APIView):
    """POST /api/incidents/<id>/notifications/retry/ - retry failed notifications (staff only)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        if not (user.is_superuser or user.role in ('security', 'admin')):
            raise PermissionDenied('Only security staff or admins can retry notifications.')
        incident = get_object_or_404(incidents_for_user(user), pk=pk)
        if incident.status in ('RESOLVED', 'CANCELLED'):
            return Response(
                {'detail': 'Cannot retry notifications for a closed incident.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(retry_failed(incident))