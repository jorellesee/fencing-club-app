from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APITestCase

from .models import Attendance, FencingClass, Member

SGT = ZoneInfo('Asia/Singapore')


def at(day, hour):
    """A Singapore time in the week of Mon 19 Oct 2026."""
    return datetime(2026, 10, day, hour, tzinfo=SGT)


class ModelTests(TestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18)
        )

    def test_member_can_only_appear_once_per_class(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='absent')

    def test_deleting_class_deletes_its_attendance(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')
        self.junior.delete()
        self.assertEqual(Attendance.objects.count(), 0)

class ClassApiTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.sam = Member.objects.create(name='Sam Lee')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), capacity=12
        )

    def test_logged_out_users_are_refused(self):
        self.client.logout()
        response = self.client.get('/api/classes/')
        self.assertEqual(response.status_code, 403)

    def test_non_managers_are_refused(self):
        coach = User.objects.create_user('coach')
        self.client.force_login(coach)
        response = self.client.get('/api/classes/')
        self.assertEqual(response.status_code, 403)

    def test_week_filter_returns_overlapping_classes(self):
        FencingClass.objects.create(name='Last week', start=at(12, 17), end=at(12, 18))
        FencingClass.objects.create(name='Overnight camp', start=at(18, 22), end=at(19, 2))
        week = {'start': at(19, 0).isoformat(), 'end': at(26, 0).isoformat()}

        response = self.client.get('/api/classes/', week)

        names = sorted(c['name'] for c in response.json())
        self.assertEqual(names, ['Junior Foil', 'Overnight camp'])

    def test_class_includes_headcounts(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')
        Attendance.objects.create(fencing_class=self.junior, member=self.sam, status='absent')

        response = self.client.get(f'/api/classes/{self.junior.id}/')

        self.assertEqual(response.json()['member_count'], 2)
        self.assertEqual(response.json()['present_count'], 1)

    def test_dragging_a_class_saves_new_times(self):
        new_times = {'start': at(22, 18).isoformat(), 'end': at(22, 19).isoformat()}

        response = self.client.patch(f'/api/classes/{self.junior.id}/', new_times)

        self.assertEqual(response.status_code, 200)
        self.junior.refresh_from_db()
        self.assertEqual(self.junior.start, at(22, 18))
        self.assertEqual(self.junior.end, at(22, 19))

    def test_class_cannot_end_before_it_starts(self):
        response = self.client.patch(
            f'/api/classes/{self.junior.id}/', {'end': at(20, 16).isoformat()}
        )

        self.assertEqual(response.status_code, 400)
        self.junior.refresh_from_db()
        self.assertEqual(self.junior.end, at(20, 18))


class AttendanceApiTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18)
        )

    def test_adding_a_member_to_a_class(self):
        response = self.client.post('/api/attendance/', {
            'fencing_class': self.junior.id, 'member': self.alex.id, 'status': 'enrolled',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['member_name'], 'Alex Tan')

    def test_adding_the_same_member_twice_is_refused(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='enrolled')

        response = self.client.post('/api/attendance/', {
            'fencing_class': self.junior.id, 'member': self.alex.id, 'status': 'enrolled',
        })

        self.assertEqual(response.status_code, 400)

    def test_marking_a_member_present(self):
        row = Attendance.objects.create(
            fencing_class=self.junior, member=self.alex, status='enrolled'
        )

        response = self.client.patch(f'/api/attendance/{row.id}/', {'status': 'present'})

        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.status, 'present')


class RepeatTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach='Coach Lim'
        )
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')

    def repeat(self, fencing_class, until):
        return self.client.post(f'/api/classes/{fencing_class.id}/repeat/', {'until': until})

    def test_repeat_creates_weekly_copies_until_the_date(self):
        response = self.repeat(self.junior, '2026-11-10')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['created'], 3)
        starts = list(FencingClass.objects.values_list('start', flat=True))
        self.assertEqual(starts, [at(20, 17) + timedelta(weeks=n) for n in range(4)])

    def test_copies_share_a_series_and_details(self):
        self.repeat(self.junior, '2026-11-03')

        self.junior.refresh_from_db()
        copies = FencingClass.objects.exclude(id=self.junior.id)
        self.assertIsNotNone(self.junior.series)
        for copy in copies:
            self.assertEqual(copy.series, self.junior.series)
            self.assertEqual(copy.coach, 'Coach Lim')

    def test_copies_enrol_the_same_members(self):
        self.repeat(self.junior, '2026-10-27')

        copy = FencingClass.objects.get(start=at(27, 17))
        self.assertEqual(list(copy.attendance.values_list('member', 'status')),
                         [(self.alex.id, 'enrolled')])

    def test_repeat_is_limited_to_one_year(self):
        response = self.repeat(self.junior, '2028-01-01')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FencingClass.objects.count(), 1)

    def test_repeat_only_from_the_last_class_in_a_series(self):
        self.repeat(self.junior, '2026-11-03')

        response = self.repeat(self.junior, '2026-12-01')

        self.assertEqual(response.status_code, 400)

    def test_delete_following_keeps_earlier_classes(self):
        self.repeat(self.junior, '2026-11-10')
        second = FencingClass.objects.get(start=at(27, 17))

        response = self.client.post(f'/api/classes/{second.id}/delete-following/')

        self.assertEqual(response.json()['deleted'], 3)
        self.assertEqual(list(FencingClass.objects.all()), [self.junior])
