import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Attendance, Coach, FencingClass, LessonRequest, Member, Profile

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
        lim = Coach.objects.create(name='Coach Lim')
        response = self.client.post('/api/classes/', {
            'name': 'Sabre Basics', 'start': at(23, 18).isoformat(), 'end': at(23, 19).isoformat(),
            'coach': lim.id, 'location': 'Hall A', 'capacity': 10,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['coach_name'], 'Coach Lim')
        created = FencingClass.objects.get(name='Sabre Basics')
        self.assertEqual((created.coach, created.location, created.capacity), (lim, 'Hall A', 10))

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
        self.lim = Coach.objects.create(name='Coach Lim')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach=self.lim,
            location='Hall A', weapon='foil',
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
            self.assertEqual(copy.coach, self.lim)
            self.assertEqual(copy.location, 'Hall A')
            self.assertEqual(copy.weapon, 'foil')

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

    def test_update_following_changes_this_and_later_classes_only(self):
        self.repeat(self.junior, '2026-11-10')
        series = list(FencingClass.objects.order_by('start'))
        response = self.client.post(
            f'/api/classes/{series[1].id}/update-following/',
            {'name': 'Tuesday Foil HA Class', 'start': at(27, 9).isoformat()},
        )
        self.assertEqual(response.data, {'updated': 3})
        names = list(FencingClass.objects.order_by('start').values_list('name', flat=True))
        self.assertEqual(names, ['Junior Foil'] + ['Tuesday Foil HA Class'] * 3)
        series[1].refresh_from_db()
        self.assertEqual(series[1].start, at(27, 17))  # times are never copied

    def test_update_following_validates(self):
        self.repeat(self.junior, '2026-11-03')
        response = self.client.post(
            f'/api/classes/{self.junior.id}/update-following/', {'weapon': 'lightsaber'}
        )
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
        self.lim = Coach.objects.create(name='Coach Lim')
        wong = Coach.objects.create(name='Coach Wong')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach=self.lim,
            location='Hall A', weapon='foil',
        )
        self.senior = FencingClass.objects.create(
            name='Senior Epee', start=at(21, 19), end=at(21, 21), coach=wong,
            location='Hall B',
        )
        FencingClass.objects.create(
            name='Open Bouting', start=at(22, 19), end=at(22, 21), coach=self.lim,
            location='Hall A',
        )
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')
        Attendance.objects.create(fencing_class=self.junior, member=self.sam, status='enrolled')
        Attendance.objects.create(fencing_class=self.senior, member=self.sam, status='present')

    def names(self, response):
        return [c['name'] for c in response.data]

    def test_coach_filter(self):
        response = self.client.get('/api/classes/', {'coach': self.lim.id})
        self.assertEqual(self.names(response), ['Junior Foil', 'Open Bouting'])

    def test_member_filter(self):
        response = self.client.get('/api/classes/', {'member': self.sam.id})
        self.assertEqual(self.names(response), ['Junior Foil', 'Senior Epee'])

    def test_member_filter_keeps_whole_class_counts(self):
        response = self.client.get('/api/classes/', {'member': self.alex.id})
        junior = response.data[0]
        self.assertEqual(junior['member_count'], 2)
        self.assertEqual(junior['present_count'], 1)

    def test_location_filter(self):
        response = self.client.get('/api/classes/', {'location': 'Hall A'})
        self.assertEqual(self.names(response), ['Junior Foil', 'Open Bouting'])

    def test_filters_combine(self):
        response = self.client.get('/api/classes/', {'location': 'Hall A', 'member': self.sam.id})
        self.assertEqual(self.names(response), ['Junior Foil'])

    def test_weapon_filter(self):
        response = self.client.get('/api/classes/', {'weapon': 'foil'})
        self.assertEqual(self.names(response), ['Junior Foil'])

    def test_locations_lists_each_name_once(self):
        response = self.client.get('/api/classes/locations/')
        self.assertEqual(response.data, ['Hall A', 'Hall B'])


class CoachApiTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.lim = Coach.objects.create(name='Coach Lim')
        FencingClass.objects.create(
            name='Past', start=at(20, 17), end=at(20, 18), coach=self.lim
        )

    def test_creating_and_editing_a_coach(self):
        response = self.client.post('/api/coaches/', {'name': 'Coach Ng', 'weapon': 'sabre'})
        self.assertEqual(response.status_code, 201)
        response = self.client.patch(
            f'/api/coaches/{response.data["id"]}/', {'email': 'ng@example.com'}
        )
        self.assertEqual(response.data['email'], 'ng@example.com')

    def test_names_are_unique(self):
        response = self.client.post('/api/coaches/', {'name': 'Coach Lim'})
        self.assertEqual(response.status_code, 400)

    def test_counts_classes_and_finds_the_next_one(self):
        future = timezone.now() + timedelta(days=3)
        FencingClass.objects.create(
            name='Soon', start=future, end=future + timedelta(hours=1), coach=self.lim
        )
        coach = self.client.get(f'/api/coaches/{self.lim.id}/').data
        self.assertEqual(coach['class_count'], 2)
        self.assertEqual(coach['next_class'], future.astimezone(SGT).isoformat())

    def test_deleting_a_coach_keeps_their_classes(self):
        self.lim.delete()
        self.assertIsNone(FencingClass.objects.get(name='Past').coach)


class MemberEditTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.lim = Coach.objects.create(name='Coach Lim')

    def test_editing_a_member(self):
        response = self.client.patch(
            f'/api/members/{self.alex.id}/', {'phone': '9123 4567', 'active': False}
        )
        self.assertEqual(response.status_code, 200)
        self.alex.refresh_from_db()
        self.assertEqual((self.alex.phone, self.alex.active), ('9123 4567', False))

    def test_setting_a_primary_coach(self):
        response = self.client.patch(
            f'/api/members/{self.alex.id}/', {'primary_coach': self.lim.id}
        )
        self.assertEqual(response.data['primary_coach_name'], 'Coach Lim')

    def test_filtering_by_primary_coach(self):
        Member.objects.create(name='Sam Lee', primary_coach=self.lim)
        response = self.client.get('/api/members/', {'primary_coach': self.lim.id})
        self.assertEqual([m['name'] for m in response.data], ['Sam Lee'])

    def test_deleting_the_coach_keeps_the_member(self):
        self.alex.primary_coach = self.lim
        self.alex.save()
        self.lim.delete()
        self.alex.refresh_from_db()
        self.assertIsNone(self.alex.primary_coach)


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
        self.lim = Coach.objects.create(name='Coach Lim')
        self.mine = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach=self.lim
        )
        self.theirs = FencingClass.objects.create(
            name='Senior Épée', start=at(21, 19), end=at(21, 20),
            coach=Coach.objects.create(name='Coach Ng'),
        )
        self.my_row = Attendance.objects.create(
            fencing_class=self.mine, member=self.alex, status='enrolled'
        )
        self.their_row = Attendance.objects.create(
            fencing_class=self.theirs, member=self.alex, status='enrolled'
        )
        self.user = User.objects.create_user('lim')
        Profile.objects.create(user=self.user, role='coach', coach=self.lim)
        self.client.force_login(self.user)

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

    def test_a_login_whose_coach_was_deleted_edits_nothing(self):
        unassigned = FencingClass.objects.create(name='Open', start=at(22, 17), end=at(22, 18))
        self.lim.delete()
        notes = self.client.patch(f'/api/classes/{unassigned.id}/', {'notes': 'Hi'})
        self.assertEqual(notes.status_code, 403)
        self.assertEqual(self.client.get('/api/attendance/unmarked/').data, [])

    def test_can_see_but_not_change_coaches(self):
        self.assertEqual(self.client.get('/api/coaches/').status_code, 200)
        response = self.client.patch(f'/api/coaches/{self.lim.id}/', {'phone': '999'})
        self.assertEqual(response.status_code, 403)


class EnrolTests(APITestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.sam = Member.objects.create(name='Sam Lee')
        soon = timezone.now() + timedelta(days=2)
        self.open = FencingClass.objects.create(
            name='Open Sabre', start=soon, end=soon + timedelta(hours=1), capacity=2
        )
        self.past = FencingClass.objects.create(
            name='Past', start=at(20, 17), end=at(20, 18)
        )
        user = User.objects.create_user('alex')
        Profile.objects.create(user=user, role='member', member=self.alex)
        self.client.force_login(user)

    def enrol(self, fencing_class):
        return self.client.post(f'/api/classes/{fencing_class.id}/enrol/')

    def test_bookable_lists_upcoming_classes_not_joined(self):
        names = lambda: [c['name'] for c in self.client.get('/api/classes/', {'bookable': 1}).data]
        self.assertEqual(names(), ['Open Sabre'])
        self.enrol(self.open)
        self.assertEqual(names(), [])

    def test_enrolling(self):
        response = self.enrol(self.open)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.open.attendance.get().member, self.alex)
        mine = self.client.get('/api/classes/').data
        self.assertEqual([c['name'] for c in mine], ['Open Sabre'])

    def test_cannot_enrol_twice_in_the_past_or_when_full(self):
        self.enrol(self.open)
        self.assertEqual(self.enrol(self.open).status_code, 400)
        self.assertEqual(self.enrol(self.past).status_code, 404)
        self.open.capacity = 1
        self.open.save()
        other = FencingClass.objects.create(
            name='Tiny', start=self.open.start, end=self.open.end, capacity=1
        )
        Attendance.objects.create(fencing_class=other, member=self.sam, status='enrolled')
        self.assertEqual(self.enrol(other).status_code, 400)

    def test_inactive_members_cannot_enrol(self):
        self.alex.active = False
        self.alex.save()
        self.assertEqual(self.enrol(self.open).status_code, 400)

    def test_cancelling_an_enrolment(self):
        self.enrol(self.open)
        response = self.client.post(f'/api/classes/{self.open.id}/unenrol/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.open.attendance.exists())

    def test_cannot_cancel_once_marked(self):
        Attendance.objects.create(fencing_class=self.open, member=self.alex, status='excused')
        response = self.client.post(f'/api/classes/{self.open.id}/unenrol/')
        self.assertEqual(response.status_code, 400)

    def test_still_cannot_change_classes(self):
        response = self.client.patch(f'/api/classes/{self.open.id}/', {'notes': 'Hi'})
        self.assertEqual(response.status_code, 403)

    def test_coaches_cannot_enrol(self):
        coach = User.objects.create_user('lim')
        Profile.objects.create(
            user=coach, role='coach', coach=Coach.objects.create(name='Coach Lim')
        )
        self.client.force_login(coach)
        self.assertEqual(self.enrol(self.open).status_code, 403)


class LessonRequestTests(APITestCase):
    def setUp(self):
        self.lim = Coach.objects.create(name='Coach Lim')
        self.ng = Coach.objects.create(name='Coach Ng')
        self.alex = Member.objects.create(name='Alex Tan', weapon='foil', primary_coach=self.lim)
        self.sam = Member.objects.create(name='Sam Lee', primary_coach=self.lim)
        self.day = (timezone.now() + timedelta(days=3)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        self.lim_class = FencingClass.objects.create(
            name='Junior Foil', start=self.day, end=self.day + timedelta(hours=1), coach=self.lim
        )
        self.alex_user = self.login_for(self.alex)
        self.client.force_login(self.alex_user)

    def login_for(self, member):
        user = User.objects.create_user(member.name.split()[0].lower())
        Profile.objects.create(user=user, role='member', member=member)
        return user

    def at_hour(self, hour, hours=1):
        start = self.day.replace(hour=hour)
        return {'start': start.isoformat(), 'end': (start + timedelta(hours=hours)).isoformat()}

    def request(self, coach, hour, **extra):
        return self.client.post(
            '/api/lesson-requests/', {'coach': coach.id, **self.at_hour(hour), **extra}
        )

    def as_lim(self):
        user = User.objects.create_user('lim')
        Profile.objects.create(user=user, role='coach', coach=self.lim)
        self.client.force_login(user)

    def test_coaches_are_primary_coach_and_class_coaches(self):
        self.assertEqual(self.client.get('/api/lesson-requests/coaches/').data,
                         [{'id': self.lim.id, 'name': 'Coach Lim'}])
        ng_class = FencingClass.objects.create(
            name='Sabre', start=self.day, end=self.day + timedelta(hours=1), coach=self.ng
        )
        Attendance.objects.create(fencing_class=ng_class, member=self.alex, status='enrolled')
        names = [c['name'] for c in self.client.get('/api/lesson-requests/coaches/').data]
        self.assertEqual(names, ['Coach Lim', 'Coach Ng'])

    def test_requesting_a_lesson(self):
        response = self.request(self.lim, 14, note='Parry 4')
        self.assertEqual(response.status_code, 201)
        lesson = LessonRequest.objects.get()
        self.assertEqual((lesson.member, lesson.status), (self.alex, 'pending'))

    def test_only_own_coaches(self):
        self.assertEqual(self.request(self.ng, 14).status_code, 400)

    def test_cannot_request_when_coach_is_busy(self):
        self.assertEqual(self.request(self.lim, 10).status_code, 400)
        self.request(self.lim, 14)
        self.client.force_login(self.login_for(self.sam))
        self.assertEqual(self.request(self.lim, 14).status_code, 400)

    def test_cannot_request_in_the_past(self):
        response = self.client.post('/api/lesson-requests/', {
            'coach': self.lim.id, 'start': at(20, 10).isoformat(), 'end': at(20, 11).isoformat(),
        })
        self.assertEqual(response.status_code, 400)

    def test_busy_hides_what_the_coach_is_doing(self):
        self.client.force_login(self.login_for(self.sam))
        self.request(self.lim, 14)
        self.client.force_login(self.alex_user)
        response = self.client.get('/api/lesson-requests/busy/', {
            'coach': self.lim.id,
            'start': (self.day - timedelta(days=1)).isoformat(),
            'end': (self.day + timedelta(days=1)).isoformat(),
        })
        self.assertEqual(len(response.data), 2)
        self.assertEqual(set(response.data[0]), {'start', 'end'})

    def test_busy_only_for_own_coaches(self):
        response = self.client.get('/api/lesson-requests/busy/', {
            'coach': self.ng.id, 'start': self.day.isoformat(),
            'end': (self.day + timedelta(days=1)).isoformat(),
        })
        self.assertEqual(response.status_code, 400)

    def test_members_see_only_their_own_requests(self):
        self.request(self.lim, 14)
        self.client.force_login(self.login_for(self.sam))
        self.assertEqual(self.client.get('/api/lesson-requests/').data, [])

    def test_calendar_filters(self):
        self.request(self.lim, 14)
        self.request(self.lim, 16)
        response = self.client.get('/api/lesson-requests/', {
            'status': 'pending', 'coach': self.lim.id,
            'start': self.day.replace(hour=13).isoformat(),
            'end': self.day.replace(hour=15).isoformat(),
        })
        self.assertEqual(len(response.data), 1)

    def test_coach_accepts_and_it_becomes_a_class(self):
        self.request(self.lim, 14)
        lesson = LessonRequest.objects.get()
        self.as_lim()
        response = self.client.post(f'/api/lesson-requests/{lesson.id}/accept/')
        self.assertEqual(response.data['status'], 'accepted')
        fencing_class = FencingClass.objects.get(id=response.data['fencing_class'])
        self.assertEqual((fencing_class.coach, fencing_class.capacity), (self.lim, 1))
        self.assertEqual(fencing_class.attendance.get().member, self.alex)

    def test_private_lessons_are_not_bookable_by_others(self):
        self.request(self.lim, 14)
        lesson = LessonRequest.objects.get()
        self.as_lim()
        self.client.post(f'/api/lesson-requests/{lesson.id}/accept/')
        self.client.force_login(self.login_for(self.sam))
        bookable = [c['name'] for c in self.client.get('/api/classes/', {'bookable': 1}).data]
        self.assertEqual(bookable, ['Junior Foil'])
        lesson.refresh_from_db()
        response = self.client.post(f'/api/classes/{lesson.fencing_class_id}/enrol/')
        self.assertEqual(response.status_code, 404)

    def test_other_coaches_cannot_accept(self):
        self.request(self.lim, 14)
        lesson = LessonRequest.objects.get()
        user = User.objects.create_user('ng')
        Profile.objects.create(user=user, role='coach', coach=self.ng)
        self.client.force_login(user)
        response = self.client.post(f'/api/lesson-requests/{lesson.id}/accept/')
        self.assertEqual(response.status_code, 404)

    def test_decline(self):
        self.request(self.lim, 14)
        lesson = LessonRequest.objects.get()
        self.as_lim()
        self.client.post(f'/api/lesson-requests/{lesson.id}/decline/')
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, 'declined')
        self.assertEqual(FencingClass.objects.count(), 1)

    def test_cancelling_an_accepted_lesson_removes_the_class(self):
        self.request(self.lim, 14)
        lesson = LessonRequest.objects.get()
        self.as_lim()
        self.client.post(f'/api/lesson-requests/{lesson.id}/accept/')
        self.client.force_login(self.alex_user)
        response = self.client.post(f'/api/lesson-requests/{lesson.id}/cancel/')
        self.assertEqual(response.data['status'], 'cancelled')
        self.assertEqual(FencingClass.objects.count(), 1)

    def test_coaches_cannot_cancel_and_members_cannot_accept(self):
        self.request(self.lim, 14)
        lesson = LessonRequest.objects.get()
        accept = self.client.post(f'/api/lesson-requests/{lesson.id}/accept/')
        self.as_lim()
        cancel = self.client.post(f'/api/lesson-requests/{lesson.id}/cancel/')
        self.assertEqual([accept.status_code, cancel.status_code], [403, 403])


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

    def test_edits_own_name_phone_and_weapon(self):
        response = self.client.patch(
            f'/api/members/{self.alex.id}/', {'phone': '9123 4567', 'weapon': 'sabre'}
        )
        self.assertEqual(response.status_code, 200)
        self.alex.refresh_from_db()
        self.assertEqual((self.alex.phone, self.alex.weapon), ('9123 4567', 'sabre'))

    def test_cannot_edit_email_status_or_coach(self):
        for field, value in [('email', 'x@example.com'), ('active', False), ('primary_coach', '')]:
            response = self.client.patch(f'/api/members/{self.alex.id}/', {field: value})
            self.assertEqual(response.status_code, 403, field)

    def test_cannot_edit_other_members(self):
        response = self.client.patch(f'/api/members/{self.sam.id}/', {'phone': '1'})
        self.assertEqual(response.status_code, 404)

    def test_cannot_mark_attendance(self):
        response = self.client.patch(f'/api/attendance/{self.alex_row.id}/', {'status': 'absent'})
        self.assertEqual(response.status_code, 403)


class AccountTests(APITestCase):
    def setUp(self):
        cache.clear()  # login attempt counts
        self.alex = Member.objects.create(name='Alex Tan')
        self.user = User.objects.create_user(
            'alex', email='alex@example.com', password='en-garde-123'
        )
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

    def test_log_in_with_email(self):
        response = self.client.post(
            '/api/login/', {'username': 'Alex@Example.com', 'password': 'en-garde-123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

    def test_too_many_login_attempts(self):
        for _ in range(10):
            self.log_in('touché')
        self.assertEqual(self.log_in('en-garde-123').status_code, 429)


def emailed_link():
    """The /set-password/<uid>/<token> part of the last email's link."""
    return re.search(r'/set-password/(\S+)/(\S+)', mail.outbox[-1].body).group(1, 2)


class InviteTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(self.manager)
        self.alex = Member.objects.create(name='Alex Tan', email='Alex@Example.com')

    def invite_alex(self):
        return self.client.post('/api/logins/', {'member': self.alex.id}, format='json')

    def accept(self, uid, token, password='en-garde-123'):
        return self.client.post(
            f'/api/set-password/{uid}/{token}/',
            {'password': password, 'password_again': password},
            format='json',
        )

    def test_inviting_a_member_creates_a_login_without_a_password(self):
        response = self.invite_alex()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'invited')
        user = User.objects.get(username='alex@example.com')
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.member, self.alex)
        self.assertEqual(mail.outbox[0].to, ['alex@example.com'])

    def test_member_shows_login_status(self):
        self.assertIsNone(self.client.get(f'/api/members/{self.alex.id}/').data['login'])
        self.invite_alex()
        login = self.client.get(f'/api/members/{self.alex.id}/').data['login']
        self.assertEqual(login['status'], 'invited')

    def test_member_needs_an_email(self):
        sam = Member.objects.create(name='Sam Lee')
        response = self.client.post('/api/logins/', {'member': sam.id}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('member', response.data)

    def test_inviting_a_coach(self):
        lim = Coach.objects.create(name='Coach Lim', email='lim@example.com')
        response = self.client.post('/api/logins/', {'coach': lim.id}, format='json')
        self.assertEqual(response.status_code, 201)
        profile = User.objects.get(email='lim@example.com').profile
        self.assertEqual((profile.role, profile.coach), ('coach', lim))
        self.assertIn('Hi Coach Lim', mail.outbox[0].body)

    def test_coach_needs_an_email(self):
        lim = Coach.objects.create(name='Coach Lim')
        response = self.client.post('/api/logins/', {'coach': lim.id}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('coach', response.data)

    def test_email_already_used(self):
        User.objects.create_user('someone', email='alex@example.com')
        self.assertEqual(self.invite_alex().status_code, 400)

    def test_accepting_sets_password_and_logs_in(self):
        self.invite_alex()
        self.client.logout()
        uid, token = emailed_link()
        details = self.client.get(f'/api/set-password/{uid}/{token}/').json()
        self.assertEqual(details['name'], 'Alex Tan')
        self.assertTrue(details['invited'])

        response = self.accept(uid, token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['role'], 'member')
        self.assertEqual(self.client.get('/api/me/').json()['member'], self.alex.id)

    def test_links_work_once(self):
        self.invite_alex()
        uid, token = emailed_link()
        self.accept(uid, token)
        self.assertEqual(self.accept(uid, token, 'another-pass-456').status_code, 400)

    def test_weak_passwords_are_refused(self):
        self.invite_alex()
        response = self.accept(*emailed_link(), password='123')
        self.assertEqual(response.status_code, 400)
        self.assertIn('too short', response.json()['detail'])

    def test_resending_replaces_the_old_link(self):
        self.invite_alex()
        old = emailed_link()
        self.assertEqual(self.invite_alex().status_code, 200)
        self.assertEqual(self.accept(*old).status_code, 400)
        self.assertEqual(self.accept(*emailed_link()).status_code, 200)

    def test_cannot_resend_once_password_is_set(self):
        self.invite_alex()
        self.accept(*emailed_link())
        self.client.force_login(self.manager)
        login_id = User.objects.get(email='alex@example.com').id
        self.assertEqual(self.client.post(f'/api/logins/{login_id}/resend/').status_code, 400)

    def test_deactivated_logins_cannot_log_in(self):
        self.invite_alex()
        self.accept(*emailed_link())
        self.client.force_login(self.manager)
        login_id = User.objects.get(email='alex@example.com').id
        self.client.patch(f'/api/logins/{login_id}/', {'is_active': False}, format='json')
        response = self.client.post(
            '/api/login/', {'username': 'alex@example.com', 'password': 'en-garde-123'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_only_managers_can_invite(self):
        user = User.objects.create_user('lim')
        lim = Coach.objects.create(name='Coach Lim')
        Profile.objects.create(user=user, role='coach', coach=lim)
        self.client.force_login(user)
        self.assertEqual(self.invite_alex().status_code, 403)
        self.assertEqual(self.client.get('/api/logins/').status_code, 403)


class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        alex = Member.objects.create(name='Alex Tan')
        self.user = User.objects.create_user(
            'alex', email='alex@example.com', password='en-garde-123'
        )
        Profile.objects.create(user=self.user, role='member', member=alex)

    def request_reset(self, email):
        return self.client.post('/api/password-reset/', {'email': email}, format='json')

    def test_reset_emails_a_working_link(self):
        self.assertEqual(self.request_reset('ALEX@example.com').status_code, 200)
        uid, token = emailed_link()
        self.assertFalse(self.client.get(f'/api/set-password/{uid}/{token}/').json()['invited'])
        response = self.client.post(
            f'/api/set-password/{uid}/{token}/',
            {'password': 'riposte-789', 'password_again': 'riposte-789'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('riposte-789'))

    def test_unknown_email_gets_the_same_answer(self):
        known = self.request_reset('alex@example.com').json()
        unknown = self.request_reset('nobody@example.com').json()
        self.assertEqual(known, unknown)
        self.assertEqual(len(mail.outbox), 1)

    def test_logins_without_a_role_get_no_email(self):
        User.objects.create_user('nobody', email='nobody@example.com')
        self.request_reset('nobody@example.com')
        self.assertEqual(len(mail.outbox), 0)

    def test_bad_link(self):
        response = self.client.get('/api/set-password/xx/not-a-token/')
        self.assertEqual(response.status_code, 400)
