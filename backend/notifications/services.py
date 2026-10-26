import logging
import uuid

from django.contrib.auth import get_user_model
from django.utils import timezone

from contacts.models import EmergencyContact
from society.models import ResidentFlatMapping, SocietyAlertPolicy, SocietyAssignment
from .models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()

MAX_ATTEMPTS = 3


def _society_ids(resident):
    return list(
        ResidentFlatMapping.objects.filter(user=resident, is_active=True)
        .values_list('flat__block__society_id', flat=True).distinct()
    )


def build_content(incident, recipient_type):
    """Privacy: each recipient type only gets the details it is allowed to see."""
    resident = incident.resident
    name = resident.get_full_name() or resident.username
    kind = incident.get_emergency_type_display()

    if recipient_type == 'community':
        return (
            'Emergency alert in your society',
            f'A resident in your society has requested help ({kind}). '
            f'Please follow instructions from security.',
        )

    lines = [f'{name} needs help.', f'Emergency: {kind}']
    if recipient_type in ('primary_guardian', 'security') and incident.description:
        lines.append(f'Message: {incident.description}')
    if incident.location_available:
        lines.append(
            f'Location: https://maps.google.com/?q={incident.latitude},{incident.longitude}'
        )
    else:
        lines.append('Location: not available')
    return f'SOS: {kind} - {name}', '\n'.join(lines)


def get_recipients(incident):
    """Work out who should be notified, and on which channels."""
    resident = incident.resident
    society_ids = _society_ids(resident)
    recipients = []

    # 1. Verified primary guardian
    guardian = EmergencyContact.objects.filter(
        resident=resident, contact_type='primary_guardian',
        is_verified=True, is_active=True,
    ).first()
    if guardian:
        user = guardian.linked_user
        email = guardian.email or (user.email if user else '')
        channels = []
        if user:
            channels.append('push')
        channels.append('sms')
        if email:
            channels.append('email')
        if user:
            channels.append('in_app')
        recipients.append({
            'type': 'primary_guardian', 'user': user, 'name': guardian.name,
            'phone': guardian.phone, 'email': email, 'channels': channels,
        })

    # 2. Security assigned to the resident's society
    security = {}
    for a in SocietyAssignment.objects.filter(
        society_id__in=society_ids, is_active=True,
        user__role='security', user__is_active=True,
    ).select_related('user'):
        security[a.user_id] = a.user
    for user in security.values():
        recipients.append({
            'type': 'security', 'user': user,
            'name': user.get_full_name() or user.username,
            'phone': user.phone, 'email': user.email,
            'channels': ['push', 'in_app'],
        })

    # 3. Available volunteers serving the resident's society
    volunteers = {}
    for a in SocietyAssignment.objects.filter(
        society_id__in=society_ids, is_active=True, is_available=True,
        user__role='volunteer', user__is_active=True,
    ).select_related('user'):
        volunteers[a.user_id] = a.user
    for user in volunteers.values():
        recipients.append({
            'type': 'volunteer', 'user': user,
            'name': user.get_full_name() or user.username,
            'phone': user.phone, 'email': user.email,
            'channels': ['push', 'in_app'],
        })

    # 4. Community: only where the society's alert policy allows it
    allowed_ids = list(
        SocietyAlertPolicy.objects.filter(
            society_id__in=society_ids, notify_community=True
        ).values_list('society_id', flat=True)
    )
    if allowed_ids:
        neighbour_ids = ResidentFlatMapping.objects.filter(
            is_active=True, flat__block__society_id__in=allowed_ids
        ).exclude(user=resident).values_list('user_id', flat=True)
        for user in User.objects.filter(id__in=list(neighbour_ids), role='resident', is_active=True):
            recipients.append({
                'type': 'community', 'user': user,
                'name': user.get_full_name() or user.username,
                'phone': user.phone, 'email': user.email,
                'channels': ['in_app'],
            })

    return recipients


def create_notifications(incident):
    """Create one record per recipient and channel. Safe to call twice: no duplicates."""
    created = []
    for r in get_recipients(incident):
        title, body = build_content(incident, r['type'])
        who = r['user'].pk if r['user'] else (r['phone'] or r['email'])
        for channel in r['channels']:
            note, was_created = Notification.objects.get_or_create(
                incident=incident,
                dedupe_key=f"{r['type']}:{who}:{channel}",
                defaults={
                    'recipient': r['user'],
                    'recipient_type': r['type'],
                    'recipient_name': r['name'],
                    'recipient_phone': r['phone'],
                    'recipient_email': r['email'],
                    'channel': channel,
                    'title': title,
                    'message': body,
                },
            )
            if was_created:
                created.append(note)
    return created


def send_via_provider(notification):
    """
    Development mock provider. Results are labelled as simulated.
    Replace with real SMS / push / email providers later.
    """
    if notification.channel == 'sms' and not notification.recipient_phone:
        return {'success': False, 'error': 'No phone number', 'simulated': True}
    if notification.channel == 'email' and not notification.recipient_email:
        return {'success': False, 'error': 'No email address', 'simulated': True}
    if notification.channel in ('push', 'in_app') and not notification.recipient_id:
        return {'success': False, 'error': 'Recipient is not a registered user', 'simulated': True}

    print(f"[SIMULATED {notification.channel.upper()}] to {notification.recipient_name}: {notification.title}")
    return {
        'success': True,
        'provider_message_id': f'SIM-{uuid.uuid4().hex[:12]}',
        'simulated': True,
    }


def dispatch(notification):
    """Send one notification and record the result. SENT does not mean DELIVERED."""
    notification.attempt_count += 1
    notification.last_attempt_at = timezone.now()
    try:
        result = send_via_provider(notification)
    except Exception as exc:
        result = {'success': False, 'error': str(exc), 'simulated': False}

    notification.is_simulated = bool(result.get('simulated'))
    if result.get('success'):
        notification.delivery_status = 'SENT'
        notification.sent_at = timezone.now()
        notification.provider_message_id = result.get('provider_message_id', '')
        notification.failure_reason = ''
    else:
        notification.delivery_status = 'FAILED'
        notification.failure_reason = str(result.get('error', 'Unknown error'))[:500]
    notification.save()
    return notification


def notify_incident(incident):
    """Create notification records for an incident and dispatch them."""
    notes = create_notifications(incident)
    for note in notes:
        dispatch(note)
    return notes


RETRY_COOLDOWN_SECONDS = 60


def retry_failed(incident):
    """
    Retry FAILED notifications of one incident.
    Limits: max 3 attempts per notification, 60 second cooldown, and each
    notification is claimed atomically so it can never be sent twice at once.
    """
    now = timezone.now()
    result = {'retried': 0, 'skipped_max_attempts': 0, 'skipped_cooldown': 0}

    for note in Notification.objects.filter(incident=incident, delivery_status='FAILED'):
        if note.attempt_count >= MAX_ATTEMPTS:
            result['skipped_max_attempts'] += 1
            continue
        if note.last_attempt_at and (now - note.last_attempt_at).total_seconds() < RETRY_COOLDOWN_SECONDS:
            result['skipped_cooldown'] += 1
            continue

        claimed = Notification.objects.filter(
            pk=note.pk, delivery_status='FAILED'
        ).update(delivery_status='PENDING')
        if not claimed:
            continue

        note.refresh_from_db()
        dispatch(note)
        result['retried'] += 1
    return result


def update_delivery_from_provider(provider_message_id, new_status, reason=''):
    """
    Apply a provider delivery callback.
    Only a SENT notification can move to DELIVERED or FAILED. Reading a
    notification never changes its delivery status.
    """
    if new_status not in ('DELIVERED', 'FAILED'):
        raise ValueError('new_status must be DELIVERED or FAILED')
    note = Notification.objects.filter(provider_message_id=provider_message_id).first()
    if note is None:
        return None
    if note.delivery_status != 'SENT':
        return note
    note.delivery_status = new_status
    if new_status == 'DELIVERED':
        note.delivered_at = timezone.now()
    else:
        note.failure_reason = reason[:500]
    note.save()
    return note
