from contacts.models import EmergencyContact
from society.models import Society, SocietyAssignment

from .models import Incident

OPEN_STATES = ['OPEN', 'ACTIVE_RESPONSE', 'ESCALATED']


def _in_societies(society_ids):
    return Incident.objects.filter(
        resident__flat_mappings__is_active=True,
        resident__flat_mappings__flat__block__society_id__in=list(society_ids),
    ).distinct()


def incidents_for_user(user):
    """Only the incidents this user is allowed to see."""
    if user.is_superuser:
        return Incident.objects.all()

    if user.role == 'security':
        ids = SocietyAssignment.objects.filter(
            user=user, is_active=True
        ).values_list('society_id', flat=True)
        return _in_societies(ids)

    if user.role == 'admin':
        ids = Society.objects.filter(admin=user).values_list('id', flat=True)
        return _in_societies(ids)

    if user.role == 'guardian':
        resident_ids = EmergencyContact.objects.filter(
            linked_user=user, is_verified=True, is_active=True
        ).values_list('resident_id', flat=True)
        return Incident.objects.filter(resident_id__in=list(resident_ids))

    if user.role == 'volunteer':
        ids = SocietyAssignment.objects.filter(
            user=user, is_active=True, is_available=True
        ).values_list('society_id', flat=True)
        return _in_societies(ids).filter(status__in=OPEN_STATES)

    return Incident.objects.filter(resident=user)