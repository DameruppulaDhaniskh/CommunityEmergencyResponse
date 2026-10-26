from unittest import mock

from rest_framework.test import APITestCase

from contacts.models import EmergencyContact
from incidents.models import Incident
from incidents.tests import make_user, make_society, place_resident
from society.models import SocietyAlertPolicy, SocietyAssignment

from .models import Notification
from .services import notify_incident


class NotificationRoutingTests(APITestCase):
    def setUp(self):
        self.soc1, block1 = make_society('Green Meadows', 'NREG1')
        self.soc2, block2 = make_society('Lake View', 'NREG2')
        SocietyAlertPolicy.objects.create(society=self.soc1, notify_community=True)

        self.res1 = make_user('res_a', 'resident')
        self.res1.first_name = 'Asha'
        self.res1.save()
        self.neighbour = make_user('res_n', 'resident')
        self.far = make_user('res_far', 'resident')
        place_resident(self.res1, block1, '101')
        place_resident(self.neighbour, block1, '102')
        place_resident(self.far, block2, '201')

        self.sec1 = make_user('sec_a', 'security')
        self.sec2 = make_user('sec_b', 'security')
        SocietyAssignment.objects.create(society=self.soc1, user=self.sec1)
        SocietyAssignment.objects.create(society=self.soc2, user=self.sec2)

        self.vol_on = make_user('vol_on', 'volunteer')
        self.vol_off = make_user('vol_off', 'volunteer')
        SocietyAssignment.objects.create(society=self.soc1, user=self.vol_on)
        SocietyAssignment.objects.create(
            society=self.soc1, user=self.vol_off, is_available=False
        )

        self.g_ok = make_user('guard_ok', 'guardian')
        self.g_no = make_user('guard_no', 'guardian')
        EmergencyContact.objects.create(
            resident=self.res1, linked_user=self.g_ok, contact_type='primary_guardian',
            name='Guard Ok', phone='8888888888', email='guard_ok@test.com', is_verified=True,
        )
        EmergencyContact.objects.create(
            resident=self.res1, linked_user=self.g_no, contact_type='secondary_guardian',
            name='Guard No', phone='7777777777', is_verified=False,
        )

    def raise_sos(self):
        self.client.force_authenticate(self.res1)
        r = self.client.post('/api/incidents/sos/', {
            'emergency_type': 'medical', 'description': 'Chest pain',
            'latitude': '16.506200', 'longitude': '80.648000',
        })
        self.assertEqual(r.status_code, 201)
        return r.data['id']

    def notes(self, incident_id, recipient_type):
        return Notification.objects.filter(incident_id=incident_id, recipient_type=recipient_type)

    def test_recipients_and_channels(self):
        iid = self.raise_sos()
        guardian = self.notes(iid, 'primary_guardian')
        self.assertEqual(
            set(guardian.values_list('channel', flat=True)),
            {'push', 'sms', 'email', 'in_app'},
        )
        self.assertEqual(
            set(self.notes(iid, 'security').values_list('recipient_id', flat=True)),
            {self.sec1.pk},
        )
        self.assertEqual(
            set(self.notes(iid, 'volunteer').values_list('recipient_id', flat=True)),
            {self.vol_on.pk},
        )
        self.assertEqual(
            set(self.notes(iid, 'community').values_list('recipient_id', flat=True)),
            {self.neighbour.pk},
        )

    def test_unverified_guardian_gets_nothing(self):
        iid = self.raise_sos()
        self.assertFalse(
            Notification.objects.filter(incident_id=iid, recipient=self.g_no).exists()
        )

    def test_no_community_alert_without_policy(self):
        SocietyAlertPolicy.objects.all().delete()
        iid = self.raise_sos()
        self.assertEqual(self.notes(iid, 'community').count(), 0)

    def test_community_message_is_private(self):
        iid = self.raise_sos()
        note = self.notes(iid, 'community').first()
        text = note.title + note.message
        self.assertNotIn('Asha', text)
        self.assertNotIn('16.5062', text)
        self.assertNotIn('Chest pain', text)

    def test_guardian_message_has_details(self):
        iid = self.raise_sos()
        note = self.notes(iid, 'primary_guardian').first()
        self.assertIn('Asha', note.title)
        self.assertIn('16.5062', note.message)
        self.assertIn('Chest pain', note.message)

    def test_simulated_results_are_not_reported_as_delivered(self):
        iid = self.raise_sos()
        notes = Notification.objects.filter(incident_id=iid)
        self.assertGreater(notes.count(), 0)
        for n in notes:
            self.assertTrue(n.is_simulated)
            self.assertEqual(n.delivery_status, 'SENT')
            self.assertIsNone(n.delivered_at)

    def test_provider_failure_is_recorded(self):
        with mock.patch(
            'notifications.services.send_via_provider',
            return_value={'success': False, 'error': 'Provider down', 'simulated': True},
        ):
            iid = self.raise_sos()
        notes = Notification.objects.filter(incident_id=iid)
        self.assertGreater(notes.count(), 0)
        for n in notes:
            self.assertEqual(n.delivery_status, 'FAILED')
            self.assertEqual(n.failure_reason, 'Provider down')

    def test_provider_exception_is_recorded(self):
        with mock.patch(
            'notifications.services.send_via_provider', side_effect=Exception('boom')
        ):
            iid = self.raise_sos()
        for n in Notification.objects.filter(incident_id=iid):
            self.assertEqual(n.delivery_status, 'FAILED')
            self.assertIn('boom', n.failure_reason)

    def test_running_twice_creates_no_duplicates(self):
        iid = self.raise_sos()
        before = Notification.objects.filter(incident_id=iid).count()
        again = notify_incident(Incident.objects.get(pk=iid))
        self.assertEqual(again, [])
        self.assertEqual(Notification.objects.filter(incident_id=iid).count(), before)


from datetime import timedelta
from django.utils import timezone


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.soc1, block1 = make_society('Green Meadows', 'AREG1')
        self.soc2, block2 = make_society('Lake View', 'AREG2')
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

        self.guardian = make_user('guard_a', 'guardian')
        EmergencyContact.objects.create(
            resident=self.res1, linked_user=self.guardian, contact_type='primary_guardian',
            name='Guard A', phone='8888888888', email='guard_a@test.com', is_verified=True,
        )

    def raise_sos(self, provider_ok=True):
        self.client.force_authenticate(self.res1)
        if provider_ok:
            r = self.client.post('/api/incidents/sos/', {'emergency_type': 'fall'})
        else:
            with mock.patch(
                'notifications.services.send_via_provider',
                return_value={'success': False, 'error': 'Provider down', 'simulated': True},
            ):
                r = self.client.post('/api/incidents/sos/', {'emergency_type': 'fall'})
        self.assertEqual(r.status_code, 201)
        return r.data['id']

    def age_attempts(self, iid, attempts=None):
        values = {'last_attempt_at': timezone.now() - timedelta(minutes=5)}
        if attempts is not None:
            values['attempt_count'] = attempts
        Notification.objects.filter(incident_id=iid).update(**values)

    def test_user_sees_only_own_notifications(self):
        iid = self.raise_sos()
        self.client.force_authenticate(self.sec1)
        r = self.client.get('/api/notifications/')
        self.assertEqual(r.status_code, 200)
        expected = set(
            Notification.objects.filter(incident_id=iid, recipient=self.sec1)
            .values_list('id', flat=True)
        )
        self.assertEqual({n['id'] for n in r.data}, expected)
        self.client.force_authenticate(self.res2)
        self.assertEqual(self.client.get('/api/notifications/').data, [])

    def test_cannot_view_another_users_notification(self):
        iid = self.raise_sos()
        note = Notification.objects.filter(incident_id=iid, recipient=self.sec1).first()
        self.client.force_authenticate(self.sec2)
        r = self.client.get(f'/api/notifications/{note.pk}/')
        self.assertEqual(r.status_code, 404)

    def test_mark_read_does_not_change_delivery_status(self):
        iid = self.raise_sos()
        note = Notification.objects.get(incident_id=iid, recipient=self.sec1, channel='in_app')
        self.client.force_authenticate(self.sec1)
        r = self.client.patch(f'/api/notifications/{note.pk}/read/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['is_read'])
        note.refresh_from_db()
        self.assertEqual(note.delivery_status, 'SENT')
        self.assertIsNone(note.delivered_at)

    def test_push_notification_cannot_be_marked_read(self):
        iid = self.raise_sos()
        note = Notification.objects.get(incident_id=iid, recipient=self.sec1, channel='push')
        self.client.force_authenticate(self.sec1)
        r = self.client.patch(f'/api/notifications/{note.pk}/read/')
        self.assertEqual(r.status_code, 400)

    def test_cannot_mark_someone_elses_notification_read(self):
        iid = self.raise_sos()
        note = Notification.objects.get(incident_id=iid, recipient=self.sec1, channel='in_app')
        self.client.force_authenticate(self.sec2)
        r = self.client.patch(f'/api/notifications/{note.pk}/read/')
        self.assertEqual(r.status_code, 404)

    def test_security_views_incident_notification_records(self):
        iid = self.raise_sos()
        self.client.force_authenticate(self.sec1)
        r = self.client.get(f'/api/incidents/{iid}/notifications/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), Notification.objects.filter(incident_id=iid).count())
        self.assertNotIn('message', r.data[0])
        self.assertNotIn('recipient_phone', r.data[0])

    def test_security_of_other_society_cannot_view_records(self):
        iid = self.raise_sos()
        self.client.force_authenticate(self.sec2)
        r = self.client.get(f'/api/incidents/{iid}/notifications/')
        self.assertEqual(r.status_code, 404)

    def test_guardian_cannot_view_incident_notification_records(self):
        iid = self.raise_sos()
        self.client.force_authenticate(self.guardian)
        r = self.client.get(f'/api/incidents/{iid}/notifications/')
        self.assertEqual(r.status_code, 403)

    def test_resident_can_view_own_incident_records(self):
        iid = self.raise_sos()
        self.client.force_authenticate(self.res1)
        r = self.client.get(f'/api/incidents/{iid}/notifications/')
        self.assertEqual(r.status_code, 200)

    def test_retry_respects_cooldown_then_succeeds_without_duplicates(self):
        iid = self.raise_sos(provider_ok=False)
        total = Notification.objects.filter(incident_id=iid).count()
        self.assertGreater(total, 0)
        self.client.force_authenticate(self.sec1)

        r = self.client.post(f'/api/incidents/{iid}/notifications/retry/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['retried'], 0)
        self.assertEqual(r.data['skipped_cooldown'], total)

        self.age_attempts(iid)
        r = self.client.post(f'/api/incidents/{iid}/notifications/retry/')
        self.assertEqual(r.data['retried'], total)

        records = Notification.objects.filter(incident_id=iid)
        self.assertEqual(records.count(), total)
        for n in records:
            self.assertEqual(n.delivery_status, 'SENT')
            self.assertEqual(n.attempt_count, 2)

    def test_retry_stops_after_max_attempts(self):
        iid = self.raise_sos(provider_ok=False)
        total = Notification.objects.filter(incident_id=iid).count()
        self.age_attempts(iid, attempts=3)
        self.client.force_authenticate(self.sec1)
        r = self.client.post(f'/api/incidents/{iid}/notifications/retry/')
        self.assertEqual(r.data['retried'], 0)
        self.assertEqual(r.data['skipped_max_attempts'], total)

    def test_resident_cannot_retry(self):
        iid = self.raise_sos(provider_ok=False)
        self.client.force_authenticate(self.res1)
        r = self.client.post(f'/api/incidents/{iid}/notifications/retry/')
        self.assertEqual(r.status_code, 403)

    def test_retry_does_nothing_when_nothing_failed(self):
        iid = self.raise_sos()
        total = Notification.objects.filter(incident_id=iid).count()
        self.client.force_authenticate(self.sec1)
        r = self.client.post(f'/api/incidents/{iid}/notifications/retry/')
        self.assertEqual(r.data, {'retried': 0, 'skipped_max_attempts': 0, 'skipped_cooldown': 0})
        self.assertEqual(Notification.objects.filter(incident_id=iid).count(), total)


from decimal import Decimal
from .services import update_delivery_from_provider


class IncidentStorageTests(APITestCase):
    def test_incident_fields_are_stored(self):
        resident = make_user('res_s', 'resident')
        self.client.force_authenticate(resident)
        r = self.client.post('/api/incidents/sos/', {
            'emergency_type': 'accident', 'description': 'Car crash',
            'latitude': '16.506200', 'longitude': '80.648000',
            'location_accuracy': 12.5,
        })
        self.assertEqual(r.status_code, 201)
        incident = Incident.objects.get(pk=r.data['id'])
        self.assertEqual(incident.resident, resident)
        self.assertEqual(incident.emergency_type, 'accident')
        self.assertEqual(incident.description, 'Car crash')
        self.assertEqual(incident.latitude, Decimal('16.506200'))
        self.assertEqual(incident.longitude, Decimal('80.648000'))
        self.assertEqual(incident.location_accuracy, 12.5)
        self.assertEqual(incident.status, 'OPEN')
        self.assertIsNotNone(incident.location_captured_at)
        self.assertIsNone(incident.resolved_at)

    def test_sos_succeeds_if_notification_processing_crashes(self):
        resident = make_user('res_c', 'resident')
        self.client.force_authenticate(resident)
        with mock.patch('incidents.views.notify_incident', side_effect=Exception('boom')):
            r = self.client.post('/api/incidents/sos/', {'emergency_type': 'fire'})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(Incident.objects.filter(pk=r.data['id']).exists())


class DeliveryCallbackTests(APITestCase):
    def make_note(self, status, provider_id):
        resident = make_user(f'res_{provider_id}', 'resident')
        incident = Incident.objects.create(resident=resident, emergency_type='fall')
        return Notification.objects.create(
            incident=incident, recipient=resident, recipient_type='community',
            recipient_name='Test', channel='sms', title='t', message='m',
            delivery_status=status, provider_message_id=provider_id,
            dedupe_key=f'test:{provider_id}:sms',
        )

    def test_callback_marks_delivered_and_is_not_read(self):
        note = self.make_note('SENT', 'SIM-111')
        updated = update_delivery_from_provider('SIM-111', 'DELIVERED')
        self.assertEqual(updated.delivery_status, 'DELIVERED')
        self.assertIsNotNone(updated.delivered_at)
        self.assertFalse(updated.is_read)

    def test_unknown_provider_id_is_ignored(self):
        self.assertIsNone(update_delivery_from_provider('SIM-NOPE', 'DELIVERED'))

    def test_failed_notification_cannot_become_delivered(self):
        self.make_note('FAILED', 'SIM-222')
        updated = update_delivery_from_provider('SIM-222', 'DELIVERED')
        self.assertEqual(updated.delivery_status, 'FAILED')
        self.assertIsNone(updated.delivered_at)
        