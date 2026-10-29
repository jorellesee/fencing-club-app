from datetime import datetime, timedelta, timezone as dt_timezone

from club import ical, services
from club.models import Attendance, CalendarFeed, Coach, FencingClass, LessonRequest, Profile

from .base import HTMX, ClubTestCase, soon


class FeedTests(ClubTestCase):
    def feed(self, user):
        token = CalendarFeed.objects.get_or_create(user=user)[0].token
        return self.client.get(f'/calendar/{token}.ics')

    def summaries(self, user):
        response = self.feed(user)
        self.assertEqual(response.status_code, 200)
        text = response.content.decode()
        return [line[len('SUMMARY:'):] for line in text.split('\r\n') if line.startswith('SUMMARY:')]

    def test_the_feed_needs_no_login_but_a_real_token(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='enrolled')
        response = self.feed(self.alex_user)
        self.assertEqual(response['Content-Type'], 'text/calendar; charset=utf-8')
        text = response.content.decode()
        self.assertTrue(text.startswith('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:'))
        self.assertIn('X-WR-CALNAME:Fencing Club: my classes\r\n', text)
        self.assertIn(f'UID:class-{self.junior.id}@testserver\r\n', text)
        self.assertIn('DESCRIPTION:Coach: Coach Lim\r\n', text)
        self.assertTrue(text.endswith('END:VCALENDAR\r\n'))
        self.assertEqual(self.client.get('/calendar/not-a-token.ics').status_code, 404)

    def test_switched_off_logins_get_nothing(self):
        self.alex_user.is_active = False
        self.alex_user.save()
        self.assertEqual(self.feed(self.alex_user).status_code, 404)

    def test_each_role_sees_its_own_classes(self):
        ng = Coach.objects.create(name='Coach Ng')
        FencingClass.objects.create(name='Epee', start=soon(3), end=soon(3, 19), coach=ng)
        FencingClass.objects.create(name='Long ago', start=soon(-90), end=soon(-90, 19))
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='enrolled')

        self.assertEqual(self.summaries(self.manager), ['Junior Foil', 'Epee'])
        self.assertEqual(self.summaries(self.coach_user), ['Junior Foil'])
        self.assertEqual(self.summaries(self.alex_user), ['Junior Foil'])

    def test_members_see_their_own_private_lessons_only(self):
        sam_user = self.login_for(Profile.Role.MEMBER, member=self.sam)
        self.sam.primary_coach = self.lim
        self.sam.save()
        for hour, member in [(10, self.alex), (12, self.sam)]:
            lesson = LessonRequest.objects.create(
                member=member, coach=self.lim, start=soon(4, hour), end=soon(4, hour + 1)
            )
            services.accept_lesson(lesson)

        self.assertEqual(self.summaries(self.alex_user), ['Private lesson: Alex Tan'])
        self.assertEqual(self.summaries(sam_user), ['Private lesson: Sam Lee'])
        self.assertIn('Private lesson: Sam Lee', self.summaries(self.coach_user))

    def test_sync_page_shows_the_link(self):
        self.client.force_login(self.coach_user)
        response = self.client.get('/calendar-sync/')
        token = CalendarFeed.objects.get(user=self.coach_user).token
        self.assertContains(response, f'http://testserver/calendar/{token}.ics')

    def test_reset_makes_the_old_link_stop_working(self):
        old = CalendarFeed.objects.create(user=self.alex_user).token
        self.client.force_login(self.alex_user)
        self.assertEqual(self.client.get('/calendar-sync/reset/').status_code, 405)
        response = self.client.post('/calendar-sync/reset/', **HTMX)
        new = CalendarFeed.objects.get(user=self.alex_user).token
        self.assertNotEqual(new, old)
        self.assertContains(response, f'/calendar/{new}.ics')
        self.client.logout()
        self.assertEqual(self.client.get(f'/calendar/{old}.ics').status_code, 404)
        self.assertEqual(self.client.get(f'/calendar/{new}.ics').status_code, 200)

    def test_sync_page_needs_a_login(self):
        self.assertRedirects(
            self.client.get('/calendar-sync/'), '/login/?next=/calendar-sync/',
            fetch_redirect_response=False,
        )


class IcalTests(ClubTestCase):
    def test_text_is_escaped(self):
        self.assertEqual(ical.escape('a\\b; c, d\ne'), 'a\\\\b\\; c\\, d\\ne')

    def test_long_lines_fold_at_75_bytes_without_splitting_characters(self):
        line = 'DESCRIPTION:' + 'é' * 100
        folded = ical.fold(line)
        parts = folded.split('\r\n')
        self.assertTrue(all(len(part.encode()) <= 75 for part in parts))
        self.assertTrue(all(part.startswith(' ') for part in parts[1:]))
        self.assertEqual(''.join(part[1:] if i else part for i, part in enumerate(parts)), line)

    def test_times_are_utc(self):
        moment = datetime(2026, 11, 6, 10, tzinfo=dt_timezone(timedelta(hours=8)))
        self.assertEqual(ical.utc(moment), '20261106T020000Z')

    def test_events_have_their_details(self):
        self.junior.location = 'Hall 2, Level 3'
        self.junior.weapon = 'foil'
        self.junior.notes = 'Bring a mask; and gloves'
        text = ical.calendar('Club', [self.junior], 'club.example')
        self.assertIn('LOCATION:Hall 2\\, Level 3\r\n', text)
        self.assertIn('DESCRIPTION:Coach: Coach Lim\\nWeapon: Foil\\n\\nBring a mask\\; and gloves\r\n', text)
        self.assertIn('DTSTART:', text)
        self.assertNotIn('\n', text.replace('\r\n', ''))
