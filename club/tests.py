"""Tests for the club's data and rules, without going through any pages.
web/tests/ checks the pages, and who may use them."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from . import queries, services
from .models import Attendance, Coach, Member, Profile, TrainingSession
from .roles import role_of

SGT = ZoneInfo('Asia/Singapore')


def at(day, hour):
    """A Singapore time in the week of Mon 19 Oct 2026."""
    return datetime(2026, 10, day, hour, tzinfo=SGT)


def soon(days, hour=10):
    """A time `days` from now, on the hour."""
    return (timezone.localtime() + timedelta(days=days)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


def login_for(username, role, **person):
    user = User.objects.create_user(username)
    Profile.objects.create(user=user, role=role, **person)
    return user


class ModelTests(TestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.junior = TrainingSession.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18)
        )

    def test_member_can_only_appear_once_per_session(self):
        Attendance.objects.create(session=self.junior, member=self.alex, status='present')
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(session=self.junior, member=self.alex, status='absent')

    def test_deleting_session_deletes_its_attendance(self):
        Attendance.objects.create(session=self.junior, member=self.alex, status='present')
        self.junior.delete()
        self.assertEqual(Attendance.objects.count(), 0)

    def test_deleting_a_coach_keeps_their_sessions_and_members(self):
        lim = Coach.objects.create(name='Coach Lim')
        self.junior.coach = lim
        self.junior.save()
        self.alex.primary_coach = lim
        self.alex.save()
        lim.delete()
        self.junior.refresh_from_db()
        self.alex.refresh_from_db()
        self.assertIsNone(self.junior.coach)
        self.assertIsNone(self.alex.primary_coach)

    def test_member_profile_needs_a_member(self):
        profile = Profile(user=User.objects.create_user('sam'), role='member')
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_staff_are_managers(self):
        self.assertEqual(role_of(User.objects.create_user('boss', is_staff=True)), 'manager')
        self.assertIsNone(role_of(User.objects.create_user('nobody')))


class RepeatTests(TestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.lim = Coach.objects.create(name='Coach Lim')
        self.junior = TrainingSession.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach=self.lim,
            location='Hall A', weapon='foil',
        )
        Attendance.objects.create(session=self.junior, member=self.alex, status='present')

    def test_creates_weekly_copies_until_the_date(self):
        self.assertEqual(services.repeat_weekly(self.junior, date(2026, 11, 10)), 3)
        starts = list(TrainingSession.objects.values_list('start', flat=True))
        self.assertEqual(starts, [at(20, 17) + timedelta(weeks=n) for n in range(4)])

    def test_copies_share_a_series_and_details(self):
        services.repeat_weekly(self.junior, date(2026, 11, 3))
        self.junior.refresh_from_db()
        self.assertIsNotNone(self.junior.series)
        for copy in TrainingSession.objects.exclude(id=self.junior.id):
            self.assertEqual(
                (copy.series, copy.coach, copy.location, copy.weapon),
                (self.junior.series, self.lim, 'Hall A', 'foil'),
            )

    def test_copies_keep_category_and_capacity(self):
        gym = TrainingSession.objects.create(
            name='Strength', start=at(21, 7), end=at(21, 8),
            category='conditioning', capacity=1,
        )
        services.repeat_weekly(gym, date(2026, 10, 28))
        copy = TrainingSession.objects.get(start=at(28, 7))
        self.assertEqual((copy.category, copy.is_individual), ('conditioning', True))

    def test_copies_enrol_the_same_members(self):
        services.repeat_weekly(self.junior, date(2026, 10, 27))
        copy = TrainingSession.objects.get(start=at(27, 17))
        self.assertEqual(list(copy.attendance.values_list('member', 'status')),
                         [(self.alex.id, 'enrolled')])

    def test_at_most_one_year(self):
        with self.assertRaises(ValidationError):
            services.repeat_weekly(self.junior, date(2028, 1, 1))
        self.assertEqual(TrainingSession.objects.count(), 1)

    def test_only_from_the_last_session_in_a_series(self):
        services.repeat_weekly(self.junior, date(2026, 11, 3))
        with self.assertRaises(ValidationError):
            services.repeat_weekly(self.junior, date(2026, 12, 1))

    def test_following_is_this_and_later_sessions(self):
        services.repeat_weekly(self.junior, date(2026, 11, 10))
        second = TrainingSession.objects.get(start=at(27, 17))
        self.assertEqual(services.following(second).count(), 3)
        services.following(second).delete()
        self.assertEqual(list(TrainingSession.objects.all()), [self.junior])

    def test_following_needs_a_series(self):
        with self.assertRaises(ValidationError):
            services.following(self.junior)


class EnrolTests(TestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.sam = Member.objects.create(name='Sam Lee')
        self.user = login_for('alex', 'member', member=self.alex)
        self.open = TrainingSession.objects.create(
            name='Open Sabre', start=soon(2), end=soon(2, 11), capacity=2
        )

    def test_enrolling(self):
        services.enrol(self.alex, self.open)
        self.assertEqual(self.open.attendance.get().status, 'enrolled')

    def test_not_twice_in_the_past_or_when_full(self):
        services.enrol(self.alex, self.open)
        with self.assertRaises(ValidationError):
            services.enrol(self.alex, self.open)
        past = TrainingSession.objects.create(name='Past', start=at(20, 17), end=at(20, 18))
        with self.assertRaises(ValidationError):
            services.enrol(self.alex, past)
        tiny = TrainingSession.objects.create(
            name='Tiny', start=self.open.start, end=self.open.end, capacity=1
        )
        services.enrol(self.sam, tiny)
        with self.assertRaisesMessage(ValidationError, 'This session is full.'):
            services.enrol(self.alex, tiny)

    def test_inactive_members_cannot_enrol(self):
        self.alex.active = False
        self.alex.save()
        with self.assertRaises(ValidationError):
            services.own_member(self.user)

    def test_cancelling_an_enrolment(self):
        services.enrol(self.alex, self.open)
        services.unenrol(self.user, self.open)
        self.assertFalse(self.open.attendance.exists())

    def test_cannot_cancel_once_marked(self):
        Attendance.objects.create(session=self.open, member=self.alex, status='excused')
        with self.assertRaises(ValidationError):
            services.unenrol(self.user, self.open)


class LessonTests(TestCase):
    def setUp(self):
        self.lim = Coach.objects.create(name='Coach Lim')
        self.ng = Coach.objects.create(name='Coach Ng')
        self.alex = Member.objects.create(name='Alex Tan', weapon='foil', primary_coach=self.lim)
        self.sam = Member.objects.create(name='Sam Lee', primary_coach=self.lim)
        self.alex_user = login_for('alex', 'member', member=self.alex)
        self.sam_user = login_for('sam', 'member', member=self.sam)
        self.day = soon(3)
        TrainingSession.objects.create(
            name='Junior Foil', start=self.day, end=self.day + timedelta(hours=1), coach=self.lim
        )

    def ask(self, user, coach, hour, hours=1):
        start = self.day.replace(hour=hour)
        return services.request_lesson(user, coach, start, start + timedelta(hours=hours))

    def test_coaches_are_primary_coach_and_session_coaches(self):
        self.assertEqual(list(services.coaches_of(self.alex)), [self.lim])
        ng_class = TrainingSession.objects.create(
            name='Sabre', start=self.day, end=self.day + timedelta(hours=1), coach=self.ng
        )
        Attendance.objects.create(session=ng_class, member=self.alex, status='enrolled')
        self.assertEqual(list(services.coaches_of(self.alex)), [self.lim, self.ng])

    def test_requesting(self):
        lesson = self.ask(self.alex_user, self.lim, 14)
        self.assertEqual((lesson.member, lesson.status), (self.alex, 'unconfirmed'))
        self.assertEqual((lesson.is_individual, lesson.weapon), (True, 'foil'))

    def test_only_own_coaches(self):
        with self.assertRaises(ValidationError):
            self.ask(self.alex_user, self.ng, 14)

    def test_not_when_the_coach_is_busy(self):
        with self.assertRaises(ValidationError):
            self.ask(self.alex_user, self.lim, 10)  # the class
        self.ask(self.alex_user, self.lim, 14)
        with self.assertRaises(ValidationError):
            self.ask(self.sam_user, self.lim, 14)  # Alex's request

    def test_times(self):
        now = timezone.now()
        self.assertIn('start', services.lesson_time_errors(now - timedelta(hours=2), now))
        self.assertIn('end', services.lesson_time_errors(self.day, self.day))
        self.assertIn('end', services.lesson_time_errors(self.day, self.day + timedelta(hours=4)))
        self.assertEqual(services.lesson_time_errors(self.day, self.day + timedelta(hours=1)), {})

    def test_busy_hides_what_the_coach_is_doing(self):
        self.ask(self.sam_user, self.lim, 14)
        self.ask(self.alex_user, self.lim, 16)
        slots = services.busy_slots(
            self.alex, self.lim, self.day - timedelta(days=1), self.day + timedelta(days=1)
        )
        # The class and Sam's request, but not Alex's own.
        self.assertEqual(len(slots), 2)
        self.assertEqual(set(slots[0]), {'start', 'end'})

    def test_accepting_confirms_it(self):
        lesson = self.ask(self.alex_user, self.lim, 14)
        services.accept_lesson(lesson)
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, 'confirmed')
        self.assertEqual(lesson.attendance.get().member, self.alex)
        with self.assertRaises(ValidationError):
            services.accept_lesson(lesson)

    def test_not_accepted_over_a_session_made_since(self):
        lesson = self.ask(self.alex_user, self.lim, 14)
        TrainingSession.objects.create(
            name='Extra', start=lesson.start, end=lesson.end, coach=self.lim
        )
        with self.assertRaises(ValidationError):
            services.accept_lesson(lesson)

    def test_private_lessons_are_not_bookable(self):
        lesson = self.ask(self.alex_user, self.lim, 14)
        services.accept_lesson(lesson)
        names = [c.name for c in queries.bookable_sessions(self.sam_user)]
        self.assertEqual(names, ['Junior Foil'])
        self.assertFalse(queries.visible_sessions(self.sam_user).filter(id=lesson.id).exists())

    def test_capacity_decides_individual_or_group(self):
        """Blank capacity means no limit, so those are group sessions too."""
        for name, capacity in [('Solo', 1), ('Pair', 2), ('Open', None)]:
            TrainingSession.objects.create(
                name=name, start=self.day, end=self.day + timedelta(hours=1), capacity=capacity
            )
        names = {c.name for c in queries.bookable_sessions(self.sam_user)}
        self.assertEqual(names, {'Junior Foil', 'Pair', 'Open'})

    def test_requests_are_not_sessions_yet(self):
        """Everywhere that lists sessions leaves requests out until they're confirmed."""
        lesson = self.ask(self.alex_user, self.lim, 14)
        lim = login_for('lim', 'coach', coach=self.lim)
        for user in [self.alex_user, lim]:
            self.assertFalse(queries.shown_sessions(user, {}).filter(id=lesson.id).exists())
            self.assertFalse(queries.feed_sessions(user).filter(id=lesson.id).exists())
        self.assertFalse(queries.bookable_sessions(self.sam_user).filter(id=lesson.id).exists())
        self.assertFalse(queries.history(self.alex).exists())
        self.assertEqual(queries.coaches().get(id=self.lim.id).session_count, 1)
        self.assertFalse(queries.can_edit_session(lim, lesson))
        self.assertEqual(list(queries.shown_requests(lim, {})), [lesson])

    def test_declining_deletes_it(self):
        lesson = self.ask(self.alex_user, self.lim, 14)
        services.decline_lesson(lesson)
        self.assertEqual(TrainingSession.objects.count(), 1)
        self.assertFalse(Attendance.objects.exists())

    def test_cancelling_a_confirmed_lesson_deletes_it(self):
        lesson = self.ask(self.alex_user, self.lim, 14)
        services.accept_lesson(lesson)
        services.cancel_lesson(lesson)
        self.assertEqual(TrainingSession.objects.count(), 1)

    def test_members_cancel_lessons_rather_than_unenrol(self):
        lesson = self.ask(self.alex_user, self.lim, 14)
        services.accept_lesson(lesson)
        with self.assertRaises(ValidationError):
            services.unenrol(self.alex_user, lesson)


class InviteTests(TestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan', email='Alex@Example.com')

    def test_inviting_creates_a_login_without_a_password(self):
        user, created = services.invite(member=self.alex)
        self.assertTrue(created)
        self.assertEqual(user.username, 'alex@example.com')
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.member, self.alex)
        self.assertEqual(mail.outbox[0].to, ['alex@example.com'])

    def test_inviting_a_coach(self):
        lim = Coach.objects.create(name='Coach Lim', email='lim@example.com')
        user, _ = services.invite(coach=lim)
        self.assertEqual((user.profile.role, user.profile.coach), ('coach', lim))
        self.assertIn('Hi Coach Lim', mail.outbox[0].body)

    def test_needs_an_email(self):
        with self.assertRaises(ValidationError):
            services.invite(member=Member.objects.create(name='Sam Lee'))
        with self.assertRaises(ValidationError):
            services.invite(coach=Coach.objects.create(name='Coach Lim'))

    def test_email_already_used(self):
        User.objects.create_user('someone', email='alex@example.com')
        with self.assertRaises(ValidationError):
            services.invite(member=self.alex)

    def test_inviting_again_resends(self):
        services.invite(member=self.alex)
        _, created = services.invite(member=self.alex)
        self.assertFalse(created)
        self.assertEqual(len(mail.outbox), 2)

    def test_cannot_resend_once_password_is_set(self):
        user, _ = services.invite(member=self.alex)
        user.set_password('en-garde-123')
        user.save()
        with self.assertRaises(ValidationError):
            services.send_again(user)

    def test_log_in_with_email(self):
        services.invite(member=self.alex)
        self.assertEqual(services.username_for(' ALEX@example.com '), 'alex@example.com')
        self.assertEqual(services.username_for('someone'), 'someone')


class QueryTests(TestCase):
    """Who sees what. Members and coaches see less than managers."""

    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.sam = Member.objects.create(name='Sam Lee')
        self.lim = Coach.objects.create(name='Coach Lim')
        wong = Coach.objects.create(name='Coach Wong')
        self.junior = TrainingSession.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach=self.lim,
            location='Hall A', weapon='foil',
        )
        self.senior = TrainingSession.objects.create(
            name='Senior Epee', start=at(21, 19), end=at(21, 21), coach=wong, location='Hall B',
        )
        TrainingSession.objects.create(
            name='Open Bouting', start=at(22, 19), end=at(22, 21), coach=self.lim,
            location='Hall A',
        )
        Attendance.objects.create(session=self.junior, member=self.alex, status='present')
        Attendance.objects.create(session=self.junior, member=self.sam, status='enrolled')
        Attendance.objects.create(session=self.senior, member=self.sam, status='present')
        self.manager = User.objects.create_user('manager', is_staff=True)

    def names(self, **filters):
        return [c.name for c in queries.shown_sessions(self.manager, filters)]

    def test_filters(self):
        self.assertEqual(self.names(coach=self.lim.id), ['Junior Foil', 'Open Bouting'])
        self.assertEqual(self.names(member=self.sam.id), ['Junior Foil', 'Senior Epee'])
        self.assertEqual(self.names(location='Hall A'), ['Junior Foil', 'Open Bouting'])
        self.assertEqual(self.names(weapon='foil'), ['Junior Foil'])
        self.assertEqual(self.names(location='Hall A', member=self.sam.id), ['Junior Foil'])

    def test_member_filter_keeps_whole_session_counts(self):
        junior = queries.shown_sessions(self.manager, {'member': self.alex.id}).get()
        self.assertEqual((junior.member_count, junior.present_count), (2, 1))

    def test_sessions_are_in_time_order(self):
        early = TrainingSession.objects.create(name='Early', start=at(19, 7), end=at(19, 8))
        self.assertEqual(queries.shown_sessions(self.manager, {})[0], early)

    def test_locations_lists_each_name_once(self):
        self.assertEqual(list(queries.locations()), ['Hall A', 'Hall B'])

    def test_members_see_only_their_sessions_with_whole_session_counts(self):
        alex = login_for('alex', 'member', member=self.alex)
        mine = queries.shown_sessions(alex, {'coach': self.lim.id})
        self.assertEqual([c.name for c in mine], ['Junior Foil'])
        self.assertEqual(mine[0].member_count, 2)
        self.assertEqual([m.name for m in queries.visible_members(alex)], ['Alex Tan'])

    def test_coaches_calendar_shows_their_sessions_but_they_can_open_any(self):
        lim = login_for('lim', 'coach', coach=self.lim)
        shown = [c.name for c in queries.shown_sessions(lim, {})]
        self.assertEqual(shown, ['Junior Foil', 'Open Bouting'])
        self.assertEqual(queries.visible_sessions(lim).count(), 3)
        self.assertTrue(queries.can_edit_session(lim, self.junior))
        self.assertFalse(queries.can_edit_session(lim, self.senior))

    def test_a_coach_login_without_a_coach_edits_nothing(self):
        lim = login_for('lim', 'coach', coach=self.lim)
        open_class = TrainingSession.objects.create(name='Open', start=at(22, 17), end=at(22, 18))
        self.lim.delete()
        lim.refresh_from_db()
        self.assertFalse(queries.can_edit_session(lim, open_class))
        self.assertFalse(queries.shown_sessions(lim, {}).exists())

    def test_member_stats(self):
        statuses = ['present', 'absent', 'excused', 'enrolled']
        for day, status in zip(range(23, 27), statuses):
            session = TrainingSession.objects.create(
                name='Junior Foil', start=at(day, 17), end=at(day, 18)
            )
            Attendance.objects.create(session=session, member=self.alex, status=status)
        alex = queries.members().get(id=self.alex.id)
        # Present on the 20th and 23rd; only present and absent count as marked.
        self.assertEqual((alex.present_count, alex.marked_count), (2, 3))
        self.assertEqual(alex.last_present, at(23, 17))
        history = [row.status for row in queries.history(alex)]
        self.assertEqual(history[:2], ['enrolled', 'excused'])

    def test_coach_counts_and_next_session(self):
        TrainingSession.objects.create(
            name='Soon', start=soon(3), end=soon(3, 11), coach=self.lim
        )
        lim = queries.coaches().get(id=self.lim.id)
        self.assertEqual((lim.session_count, lim.next_session), (3, soon(3)))

    def test_category_filter(self):
        TrainingSession.objects.create(
            name='Strength', start=at(22, 17), end=at(22, 18), category='conditioning'
        )
        self.assertEqual(self.names(category='conditioning'), ['Strength'])
        self.assertNotIn('Strength', self.names(category='fencing'))

    def test_requests_on_the_calendar(self):
        start = soon(3)
        alex = login_for('alex', 'member', member=self.alex)
        services.request_lesson(alex, self.lim, start, start + timedelta(hours=1))
        self.assertEqual(queries.shown_requests(self.manager, {}).count(), 1)
        self.assertEqual(queries.shown_requests(self.manager, {'location': 'Hall A'}).count(), 0)
        self.assertEqual(queries.shown_requests(self.manager, {'member': self.alex.id}).count(), 1)
        sam = login_for('sam', 'member', member=self.sam)
        self.assertEqual(queries.shown_requests(sam, {}).count(), 0)
        ng = login_for('ng', 'coach', coach=Coach.objects.create(name='Coach Ng'))
        self.assertEqual(queries.visible_lessons(ng).count(), 0)
