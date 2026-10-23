from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Attendance, FencingClass, Member, Profile

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

    def test_logins_without_a_role_are_refused(self):
        nobody = User.objects.create_user('nobody')
        self.client.force_login(nobody)
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

    def test_creating_a_class_with_details(self):
        response = self.client.post('/api/classes/', {
            'name': 'Sabre Basics', 'start': at(23, 18).isoformat(), 'end': at(23, 19).isoformat(),
            'coach': 'Coach Lim', 'location': 'Hall A', 'capacity': 10,
        })
        self.assertEqual(response.status_code, 201)
        created = FencingClass.objects.get(name='Sabre Basics')
        self.assertEqual((created.location, created.capacity), ('Hall A', 10))

    def test_creating_a_member(self):
        # JSON, like React sends. In form data, a missing checkbox means False.
        response = self.client.post(
            '/api/members/', {'name': 'Jo Lim', 'weapon': 'sabre'}, format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Member.objects.get(name='Jo Lim').active)

    def test_member_needs_a_name(self):
        response = self.client.post('/api/members/', {'name': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.data)


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
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach='Coach Lim',
            location='Hall A',
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
            self.assertEqual(copy.location, 'Hall A')

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


class FilterTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.sam = Member.objects.create(name='Sam Lee')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach='Coach Lim',
            location='Hall A',
        )
        self.senior = FencingClass.objects.create(
            name='Senior Epee', start=at(21, 19), end=at(21, 21), coach='Coach Wong',
            location='Hall B',
        )
        FencingClass.objects.create(
            name='Open Bouting', start=at(22, 19), end=at(22, 21), coach='Coach Lim',
            location='Hall A',
        )
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')
        Attendance.objects.create(fencing_class=self.junior, member=self.sam, status='enrolled')
        Attendance.objects.create(fencing_class=self.senior, member=self.sam, status='present')

    def names(self, response):
        return [c['name'] for c in response.data]

    def test_coach_filter(self):
        response = self.client.get('/api/classes/', {'coach': 'Coach Lim'})
        self.assertEqual(self.names(response), ['Junior Foil', 'Open Bouting'])

    def test_member_filter(self):
        response = self.client.get('/api/classes/', {'member': self.sam.id})
        self.assertEqual(self.names(response), ['Junior Foil', 'Senior Epee'])

    def test_member_filter_keeps_whole_class_counts(self):
        response = self.client.get('/api/classes/', {'member': self.alex.id})
        junior = response.data[0]
        self.assertEqual(junior['member_count'], 2)
        self.assertEqual(junior['present_count'], 1)

    def test_coaches_lists_each_name_once(self):
        response = self.client.get('/api/classes/coaches/')
        self.assertEqual(response.data, ['Coach Lim', 'Coach Wong'])

    def test_location_filter(self):
        response = self.client.get('/api/classes/', {'location': 'Hall A'})
        self.assertEqual(self.names(response), ['Junior Foil', 'Open Bouting'])

    def test_filters_combine(self):
        response = self.client.get('/api/classes/', {'location': 'Hall A', 'member': self.sam.id})
        self.assertEqual(self.names(response), ['Junior Foil'])

    def test_locations_lists_each_name_once(self):
        response = self.client.get('/api/classes/locations/')
        self.assertEqual(response.data, ['Hall A', 'Hall B'])


class MemberStatsTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        statuses = ['present', 'present', 'absent', 'excused', 'enrolled']
        for day, status in zip(range(19, 24), statuses):
            fencing_class = FencingClass.objects.create(
                name='Junior Foil', start=at(day, 17), end=at(day, 18)
            )
            Attendance.objects.create(fencing_class=fencing_class, member=self.alex, status=status)

    def test_counts_only_present_and_absent_as_marked(self):
        alex = self.client.get(f'/api/members/{self.alex.id}/').data
        self.assertEqual(alex['present_count'], 2)
        self.assertEqual(alex['marked_count'], 3)

    def test_last_present_is_the_latest_present_class(self):
        alex = self.client.get(f'/api/members/{self.alex.id}/').data
        self.assertEqual(alex['last_present'], at(20, 17).isoformat())

    def test_history_is_newest_first(self):
        rows = self.client.get('/api/attendance/', {'member': self.alex.id}).data
        self.assertEqual([row['status'] for row in rows][:2], ['enrolled', 'excused'])
        self.assertEqual(rows[0]['class_name'], 'Junior Foil')


class UnmarkedTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.sam = Member.objects.create(name='Sam Lee')

    def add(self, start, end, member, status):
        fencing_class = FencingClass.objects.create(name='Junior Foil', start=start, end=end)
        Attendance.objects.create(fencing_class=fencing_class, member=member, status=status)

    def test_lists_enrolled_rows_in_past_classes_only(self):
        past = timezone.now() - timedelta(days=1)
        future = timezone.now() + timedelta(days=1)
        self.add(past, past + timedelta(hours=1), self.alex, 'enrolled')
        self.add(past, past + timedelta(hours=1), self.sam, 'present')
        self.add(future, future + timedelta(hours=1), self.sam, 'enrolled')

        rows = self.client.get('/api/attendance/unmarked/').data

        self.assertEqual([row['member_name'] for row in rows], ['Alex Tan'])


class CoachTests(APITestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.mine = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach='Coach Lim'
        )
        self.theirs = FencingClass.objects.create(
            name='Senior Épée', start=at(21, 19), end=at(21, 20), coach='Coach Ng'
        )
        self.my_row = Attendance.objects.create(
            fencing_class=self.mine, member=self.alex, status='enrolled'
        )
        self.their_row = Attendance.objects.create(
            fencing_class=self.theirs, member=self.alex, status='enrolled'
        )
        coach = User.objects.create_user('lim')
        Profile.objects.create(user=coach, role='coach', coach_name='Coach Lim')
        self.client.force_login(coach)

    def test_sees_every_class(self):
        response = self.client.get('/api/classes/')
        self.assertEqual(len(response.data), 2)

    def test_marks_attendance_in_own_class(self):
        response = self.client.patch(f'/api/attendance/{self.my_row.id}/', {'status': 'present'})
        self.assertEqual(response.status_code, 200)

    def test_cannot_mark_another_coachs_class(self):
        response = self.client.patch(
            f'/api/attendance/{self.their_row.id}/', {'status': 'present'}
        )
        self.assertEqual(response.status_code, 403)

    def test_can_only_change_status(self):
        response = self.client.patch(
            f'/api/attendance/{self.my_row.id}/', {'status': 'present', 'fencing_class': self.theirs.id}
        )
        self.assertEqual(response.status_code, 403)

    def test_edits_notes_but_not_times_of_own_class(self):
        notes = self.client.patch(f'/api/classes/{self.mine.id}/', {'notes': 'Bring masks'})
        times = self.client.patch(f'/api/classes/{self.mine.id}/', {'start': at(20, 16)})
        self.assertEqual(notes.status_code, 200)
        self.assertEqual(times.status_code, 403)

    def test_cannot_create_delete_or_repeat_classes(self):
        create = self.client.post(
            '/api/classes/', {'name': 'New', 'start': at(22, 17), 'end': at(22, 18)}
        )
        delete = self.client.delete(f'/api/classes/{self.mine.id}/')
        repeat = self.client.post(f'/api/classes/{self.mine.id}/repeat/', {'until': '2026-11-30'})
        self.assertEqual(
            [create.status_code, delete.status_code, repeat.status_code], [403, 403, 403]
        )

    def test_cannot_change_members(self):
        response = self.client.patch(f'/api/members/{self.alex.id}/', {'name': 'Alexander'})
        self.assertEqual(response.status_code, 403)

    def test_cannot_create_members(self):
        response = self.client.post('/api/members/', {'name': 'Jo Lim'})
        self.assertEqual(response.status_code, 403)

    def test_needs_marking_shows_only_own_classes(self):
        rows = self.client.get('/api/attendance/unmarked/').data
        self.assertEqual([row['id'] for row in rows], [self.my_row.id])


class MemberRoleTests(APITestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.sam = Member.objects.create(name='Sam Lee')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18)
        )
        self.senior = FencingClass.objects.create(
            name='Senior Épée', start=at(21, 19), end=at(21, 20)
        )
        self.alex_row = Attendance.objects.create(
            fencing_class=self.junior, member=self.alex, status='present'
        )
        Attendance.objects.create(fencing_class=self.junior, member=self.sam, status='present')
        Attendance.objects.create(fencing_class=self.senior, member=self.sam, status='present')
        user = User.objects.create_user('alex')
        Profile.objects.create(user=user, role='member', member=self.alex)
        self.client.force_login(user)

    def test_sees_only_own_classes_with_whole_class_counts(self):
        classes = self.client.get('/api/classes/').data
        self.assertEqual([c['name'] for c in classes], ['Junior Foil'])
        self.assertEqual(classes[0]['member_count'], 2)

    def test_sees_only_own_attendance(self):
        rows = self.client.get('/api/attendance/', {'fencing_class': self.junior.id}).data
        self.assertEqual([row['member_name'] for row in rows], ['Alex Tan'])

    def test_sees_own_profile_only(self):
        own = self.client.get(f'/api/members/{self.alex.id}/')
        other = self.client.get(f'/api/members/{self.sam.id}/')
        everyone = self.client.get('/api/members/')
        self.assertEqual(
            [own.status_code, other.status_code, everyone.status_code], [200, 404, 403]
        )

    def test_cannot_mark_attendance(self):
        response = self.client.patch(f'/api/attendance/{self.alex_row.id}/', {'status': 'absent'})
        self.assertEqual(response.status_code, 403)


class AccountTests(APITestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.user = User.objects.create_user('alex', password='en-garde-123')
        Profile.objects.create(user=self.user, role='member', member=self.alex)

    def log_in(self, password):
        return self.client.post(
            '/api/login/', {'username': 'alex', 'password': password}, format='json'
        )

    def test_logged_out_me_is_null(self):
        response = self.client.get('/api/me/')
        self.assertIsNone(response.json())
        self.assertIn('csrftoken', response.cookies)

    def test_log_in_then_me(self):
        self.assertEqual(self.log_in('en-garde-123').status_code, 200)
        me = self.client.get('/api/me/').json()
        self.assertEqual(me['role'], 'member')
        self.assertEqual(me['member'], self.alex.id)

    def test_wrong_password(self):
        self.assertEqual(self.log_in('touché').status_code, 400)

    def test_login_without_a_role_is_refused(self):
        self.user.profile.delete()
        self.assertEqual(self.log_in('en-garde-123').status_code, 400)

    def test_staff_are_managers(self):
        self.client.force_login(User.objects.create_user('boss', is_staff=True))
        self.assertEqual(self.client.get('/api/me/').json()['role'], 'manager')

    def test_log_out(self):
        self.log_in('en-garde-123')
        self.client.post('/api/logout/')
        self.assertIsNone(self.client.get('/api/me/').json())

    def test_member_profile_needs_a_member(self):
        profile = Profile(user=User.objects.create_user('sam'), role='member')
        with self.assertRaises(ValidationError):
            profile.full_clean()
