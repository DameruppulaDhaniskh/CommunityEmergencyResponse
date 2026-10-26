from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Incident

User = get_user_model()


def make_user(name, role):
    return User.objects.create_user(
        username=name, email=f'{name}@test.com', password='Pass12345!',
        phone='9999999999', role=role,
    )


class IncidentCreateTests(APITestCase):
    def setUp(self):
        self.resident = make_user('res1', 'resident')
        self.other = make_user('res2', 'resident')
        self.guardian = make_user('guard1', 'guardian')

    def test_valid_resident_creates_incident(self):
        self.client.force_authenticate(self.resident)
        r = self.client.post('/api/incidents/sos/', {
            'emergency_type': 'medical', 'description': 'Help',
            'latitude': '16.506200', 'longitude': '80.648000',
        })
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['status'], 'OPEN')
        self.assertIn('id', r.data)
        self.assertIn('created_at', r.data)
        self.assertTrue(r.data['location_available'])

    def test_unauthenticated_cannot_create(self):
        r = self.client.post('/api/incidents/sos/', {'emergency_type': 'medical'})
        self.assertIn(r.status_code, (401, 403))

    def test_invalid_category_rejected(self):
        self.client.force_authenticate(self.resident)
        r = self.client.post('/api/incidents/sos/', {'emergency_type': 'alien_attack'})
        self.assertEqual(r.status_code, 400)

    def test_sos_works_without_location(self):
        self.client.force_authenticate(self.resident)
        r = self.client.post('/api/incidents/sos/', {'emergency_type': 'fall'})
        self.assertEqual(r.status_code, 201)
        self.assertFalse(r.data['location_available'])

    def test_only_one_coordinate_rejected(self):
        self.client.force_authenticate(self.resident)
        r = self.client.post('/api/incidents/sos/', {
            'emergency_type': 'fire', 'latitude': '16.5',
        })
        self.assertEqual(r.status_code, 400)

    def test_guardian_cannot_create(self):
        self.client.force_authenticate(self.guardian)
        r = self.client.post('/api/incidents/sos/', {'emergency_type': 'fire'})
        self.assertEqual(r.status_code, 403)

    def test_resident_id_in_request_is_ignored(self):
        self.client.force_authenticate(self.resident)
        r = self.client.post('/api/incidents/sos/', {
            'emergency_type': 'other', 'resident': self.other.pk,
        })
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Incident.objects.get(pk=r.data['id']).resident, self.resident)

    def test_resident_history_shows_only_own(self):
        Incident.objects.create(resident=self.resident, emergency_type='fall')
        Incident.objects.create(resident=self.other, emergency_type='fire')
        self.client.force_authenticate(self.resident)
        r = self.client.get('/api/resident/incidents/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)


from contacts.models import EmergencyContact
from society.models import (
    Society, Block, Flat, ResidentFlatMapping, SocietyAssignment,
)


def make_society(name, reg):
    society = Society.objects.create(
        name=name, registration_number=reg, address='Main Road', city='Bengaluru',
        state='Karnataka', pincode='560001', contact_email=f'{reg}@test.com',
        contact_phone='9999999999',
    )
    block = Block.objects.create(society=society, name='A')
    return society, block


def place_resident(user, block, flat_number):
    flat = Flat.objects.create(block=block, flat_number=flat_number)
    ResidentFlatMapping.objects.create(user=user, flat=flat)


class IncidentAccessTests(APITestCase):
    def setUp(self):
        self.soc1, block1 = make_society('Green Meadows', 'REG1')
        self.soc2, block2 = make_society('Lake View', 'REG2')

        self.res1 = make_user('res_a', 'resident')
        self.res2 = make_user('res_b', 'resident')
        place_resident(self.res1, block1, '101')
        place_resident(self.res2, block2, '201')

        self.sec1 = make_user('sec_a', 'security')
        self.sec2 = make_user('sec_b', 'security')
        SocietyAssignment.objects.create(society=self.soc1, user=self.sec1)
        SocietyAssignment.objects.create(society=self.soc2, user=self.sec2)

        self.vol1 = make_user('vol_a', 'volunteer')
        SocietyAssignment.objects.create(society=self.soc1, user=self.vol1)

        self.adm1 = make_user('adm_a', 'admin')
        self.soc1.admin = self.adm1
        self.soc1.save()

        self.g_ok = make_user('guard_ok', 'guardian')
        self.g_no = make_user('guard_no', 'guardian')
        EmergencyContact.objects.create(
            resident=self.res1, linked_user=self.g_ok, contact_type='primary_guardian',
            name='Guard Ok', phone='8888888888', is_verified=True,
        )
        EmergencyContact.objects.create(
            resident=self.res1, linked_user=self.g_no, contact_type='secondary_guardian',
            name='Guard No', phone='7777777777', is_verified=False,
        )

        self.inc1 = Incident.objects.create(resident=self.res1, emergency_type='medical')
        self.inc2 = Incident.objects.create(resident=self.res2, emergency_type='fire')

    def ids(self, response):
        return [i['id'] for i in response.data]

    def test_resident_sees_only_own_in_list(self):
        self.client.force_authenticate(self.res1)
        r = self.client.get('/api/incidents/')
        self.assertEqual(self.ids(r), [self.inc1.pk])

    def test_security_sees_only_own_society(self):
        self.client.force_authenticate(self.sec1)
        r = self.client.get('/api/incidents/')
        self.assertEqual(self.ids(r), [self.inc1.pk])

    def test_security_of_other_society_gets_404(self):
        self.client.force_authenticate(self.sec2)
        r = self.client.get(f'/api/incidents/{self.inc1.pk}/')
        self.assertEqual(r.status_code, 404)

    def test_only_verified_guardian_sees_incident(self):
        self.client.force_authenticate(self.g_ok)
        self.assertEqual(self.ids(self.client.get('/api/incidents/')), [self.inc1.pk])
        self.client.force_authenticate(self.g_no)
        self.assertEqual(self.ids(self.client.get('/api/incidents/')), [])

    def test_volunteer_sees_only_when_available(self):
        self.client.force_authenticate(self.vol1)
        self.assertEqual(self.ids(self.client.get('/api/incidents/')), [self.inc1.pk])
        SocietyAssignment.objects.filter(user=self.vol1).update(is_available=False)
        self.assertEqual(self.ids(self.client.get('/api/incidents/')), [])

    def test_other_resident_cannot_view_detail(self):
        self.client.force_authenticate(self.res2)
        r = self.client.get(f'/api/incidents/{self.inc1.pk}/')
        self.assertEqual(r.status_code, 404)

    def test_status_endpoint(self):
        self.client.force_authenticate(self.res1)
        r = self.client.get(f'/api/incidents/{self.inc1.pk}/status/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], 'OPEN')

    def test_society_admin_sees_own_society_only(self):
        self.client.force_authenticate(self.adm1)
        r = self.client.get('/api/incidents/')
        self.assertEqual(self.ids(r), [self.inc1.pk])

    def test_unauthenticated_cannot_list(self):
        r = self.client.get('/api/incidents/')
        self.assertIn(r.status_code, (401, 403))