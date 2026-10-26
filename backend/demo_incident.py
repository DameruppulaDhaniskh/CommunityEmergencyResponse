import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from contacts.models import EmergencyContact
from society.models import (
    Society, Block, Flat, ResidentFlatMapping, SocietyAssignment, SocietyAlertPolicy,
)

User = get_user_model()


def get_user(name, role):
    user, created = User.objects.get_or_create(
        email=f'{name}@demo.com',
        defaults={'username': name, 'phone': '9999999999', 'role': role},
    )
    if created:
        user.set_password('Pass12345!')
        user.save()
    return user


def client_for(user):
    c = APIClient(HTTP_HOST='localhost')
    c.force_authenticate(user)
    return c


# ---- Demo data ----
resident = get_user('demo_resident', 'resident')
neighbour = get_user('demo_neighbour', 'resident')
guardian = get_user('demo_guardian', 'guardian')
security = get_user('demo_security', 'security')
volunteer = get_user('demo_volunteer', 'volunteer')

society, _ = Society.objects.get_or_create(
    registration_number='DEMO-001',
    defaults={
        'name': 'Green Meadows Apartments', 'address': 'MG Road', 'city': 'Bengaluru',
        'state': 'Karnataka', 'pincode': '560001',
        'contact_email': 'demo@society.com', 'contact_phone': '9999999999',
    },
)
block, _ = Block.objects.get_or_create(society=society, name='A')
flat1, _ = Flat.objects.get_or_create(block=block, flat_number='101')
flat2, _ = Flat.objects.get_or_create(block=block, flat_number='102')
ResidentFlatMapping.objects.get_or_create(user=resident, flat=flat1)
ResidentFlatMapping.objects.get_or_create(user=neighbour, flat=flat2)
SocietyAssignment.objects.get_or_create(society=society, user=security)
SocietyAssignment.objects.get_or_create(society=society, user=volunteer)
SocietyAlertPolicy.objects.get_or_create(society=society, defaults={'notify_community': True})
EmergencyContact.objects.get_or_create(
    resident=resident, contact_type='primary_guardian',
    defaults={
        'linked_user': guardian, 'name': 'Demo Guardian', 'phone': '8888888888',
        'email': 'demo_guardian@demo.com', 'is_verified': True,
    },
)

# ---- Workflow ----
print('\n--- 1. Resident presses SOS ---')
r = client_for(resident).post('/api/incidents/sos/', {
    'emergency_type': 'medical', 'description': 'Chest pain, please help',
    'latitude': '12.971600', 'longitude': '77.594600', 'location_accuracy': 10.0,
})
print(r.status_code, dict(r.data))
incident_id = r.data['id']

print('\n--- 2. Security monitors notification records ---')
r = client_for(security).get(f'/api/incidents/{incident_id}/notifications/')
print(r.status_code, f'{len(r.data)} records')
print(f"{'RECIPIENT':<18}{'CHANNEL':<9}{'STATUS':<8}SIMULATED")
for n in r.data:
    print(f"{n['recipient_type']:<18}{n['channel']:<9}{n['delivery_status']:<8}{n['is_simulated']}")

print('\n--- 3. Security reads an in-app notification ---')
sec = client_for(security)
note = sec.get('/api/notifications/?channel=in_app').data[0]
r = sec.patch(f"/api/notifications/{note['id']}/read/")
print(r.status_code, 'is_read:', r.data['is_read'], '| delivery_status:', r.data['delivery_status'])

print('\n--- 4. Retry failed notifications ---')
r = sec.post(f'/api/incidents/{incident_id}/notifications/retry/')
print(r.status_code, dict(r.data))

print('\n--- 5. Another society member cannot see the incident ---')
r = client_for(neighbour).get(f'/api/incidents/{incident_id}/')
print(r.status_code)

print('\n--- 6. Incident status ---')
r = client_for(resident).get(f'/api/incidents/{incident_id}/status/')
print(r.status_code, dict(r.data))
