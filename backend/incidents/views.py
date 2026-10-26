import logging

from notifications.services import notify_incident

logger = logging.getLogger(__name__)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .access import incidents_for_user
from .models import Incident
from .serializers import (
    IncidentCreateSerializer, IncidentSerializer, IncidentStatusSerializer,
)

class SOSCreateView(generics.CreateAPIView):
    """POST /api/incidents/sos/ - the resident is taken from the login token only."""
    serializer_class = IncidentCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if request.user.role != 'resident':
            raise PermissionDenied('Only residents can raise an SOS.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incident = serializer.save(resident=request.user)
        try:
            notify_incident(incident)
        except Exception:
            logger.exception('Notification processing failed for incident %s', incident.pk)
        return Response(
            {
                'id': incident.pk,
                'status': incident.status,
                'created_at': incident.created_at,
                'location_available': incident.location_available,
            },
            status=status.HTTP_201_CREATED,
        )

class ResidentIncidentListView(generics.ListAPIView):
    """GET /api/resident/incidents/ - my own incident history."""
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Incident.objects.filter(resident=self.request.user)


class IncidentListView(generics.ListAPIView):
    """GET /api/incidents/ - incidents I am authorized to view."""
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'emergency_type']

    def get_queryset(self):
        return incidents_for_user(self.request.user)


class IncidentDetailView(generics.RetrieveAPIView):
    """GET /api/incidents/<id>/ - 404 if I am not allowed to see it."""
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return incidents_for_user(self.request.user)


class IncidentStatusView(generics.RetrieveAPIView):
    """GET /api/incidents/<id>/status/"""
    serializer_class = IncidentStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return incidents_for_user(self.request.user)