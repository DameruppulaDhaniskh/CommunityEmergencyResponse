from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import EmergencyContact
from .serializers import EmergencyContactSerializer, ContactVerificationSerializer
from users.permissions import IsAdminRole


class EmergencyContactListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/contacts/   — list own emergency contacts (or all for admin)
    POST /api/contacts/   — add an emergency contact
    """
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return EmergencyContact.objects.filter(is_active=True)
        return EmergencyContact.objects.filter(
            resident=user, is_active=True
        ).order_by('priority')

    def perform_create(self, serializer):
        contact = serializer.save(resident=self.request.user)
        # Automatically send verification (token generated; email is a stub)
        contact.generate_verification_token()
        contact.verification_sent_at = timezone.now()
        contact.save(update_fields=['verification_token', 'verification_sent_at'])
        # TODO: send actual email/SMS in Week 3+ notification module


class EmergencyContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/contacts/<pk>/   — view a contact
    PATCH  /api/contacts/<pk>/   — update a contact
    DELETE /api/contacts/<pk>/   — soft-delete (set is_active=False)
    """
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return EmergencyContact.objects.all()
        return EmergencyContact.objects.filter(resident=user)

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()


class ContactVerifyView(APIView):
    """
    POST /api/contacts/<pk>/verify/
    Allows a contact to confirm themselves using their verification token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            contact = EmergencyContact.objects.get(pk=pk, resident=request.user)
        except EmergencyContact.DoesNotExist:
            return Response(
                {'error': 'Contact not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ContactVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['token']
        if contact.verification_token != token:
            return Response(
                {'error': 'Invalid verification token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if contact.is_verified:
            return Response(
                {'detail': 'Contact is already verified.'},
                status=status.HTTP_200_OK,
            )

        contact.is_verified = True
        contact.verified_at = timezone.now()
        contact.verification_token = ''  # clear token after use
        contact.save(update_fields=['is_verified', 'verified_at', 'verification_token'])

        return Response(
            {'detail': 'Contact verified successfully.'},
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    """
    POST /api/contacts/<pk>/resend-verification/
    Regenerates and resends the verification token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            contact = EmergencyContact.objects.get(pk=pk, resident=request.user)
        except EmergencyContact.DoesNotExist:
            return Response(
                {'error': 'Contact not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if contact.is_verified:
            return Response(
                {'detail': 'This contact is already verified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contact.generate_verification_token()
        contact.verification_sent_at = timezone.now()
        contact.save(update_fields=['verification_token', 'verification_sent_at'])
        # TODO: send actual email/SMS in Week 3+ notification module

        return Response(
            {'detail': 'Verification resent successfully.'},
            status=status.HTTP_200_OK,
        )
