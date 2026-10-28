import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from club.models import Attendance, Coach, FencingClass, LessonRequest, Member, Profile

HTMX = {'HTTP_HX_REQUEST': 'true'}


def soon(days, hour=18):
    """A time `days` from now, on the hour, in the club's time zone."""
    day = timezone.localtime() + timedelta(days=days)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)


class ClubTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.manager = User.objects.create_user('manager', is_staff=True)
        self.lim = Coach.objects.create(name='Coach Lim', email='lim@example.com')
        self.alex = Member.objects.create(name='Alex Tan', email='alex@example.com',
                                          primary_coach=self.lim)
        self.sam = Member.objects.create(name='Sam Lee')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=soon(2), end=soon(2, 19), coach=self.lim, capacity=2
        )
        self.coach_user = self.login_for(Profile.Role.COACH, coach=self.lim)
        self.alex_user = self.login_for(Profile.Role.MEMBER, member=self.alex)

    def login_for(self, role, **person):
        user = User.objects.create_user(f'{role}-{User.objects.count()}', password='pw')
        Profile.objects.create(user=user, role=role, **person)
        return user

    def week(self):
        start = timezone.now() - timedelta(days=1)
        return {'start': start.isoformat(), 'end': (start + timedelta(days=7)).isoformat()}


class LoginTests(ClubTestCase):
    def test_pages_send_logged_out_people_to_login(self):
        response = self.client.get('/members/')
        self.assertRedirects(response, '/login/?next=/members/')

    def test_htmx_requests_redirect_the_whole_page(self):
        response = self.client.get(f'/classes/{self.junior.id}/', **HTMX)
        self.assertEqual(response['HX-Redirect'], '/login/')

    def test_logging_in_with_email(self):
        self.alex_user.email = 'alex@example.com'
        self.alex_user.save()
        response = self.client.post('/login/', {'username': 'ALEX@example.com', 'password': 'pw'})
        self.assertRedirects(response, '/')

    def test_wrong_password(self):
        response = self.client.post('/login/', {'username': self.alex_user.username, 'password': 'x'})
        self.assertContains(response, 'Wrong username or password.')

    def test_invite_link_sets_password_and_logs_in(self):
        self.client.force_login(self.manager)
        self.client.post(f'/members/{self.sam.id}/invite/')  # Sam has no email
        self.assertEqual(len(mail.outbox), 0)
        self.sam.email = 'sam@example.com'
        self.sam.save()
        response = self.client.post(f'/members/{self.sam.id}/invite/')
        self.assertContains(response, 'Sent to sam@example.com')
        self.client.logout()

        # Emailed links have no trailing slash; Django's APPEND_SLASH adds it.
        link = re.search(r'(/set-password/\S+)', mail.outbox[-1].body).group(1) + '/'
        self.assertContains(self.client.get(link), 'Welcome, Sam Lee')
        response = self.client.post(link, {
            'new_password1': 'a-long-passphrase', 'new_password2': 'a-long-passphrase',
        })
        self.assertRedirects(response, '/')
        self.assertContains(self.client.get('/book/'), 'Book a class')


class RoleTests(ClubTestCase):
    def test_each_role_sees_its_own_sidebar(self):
        self.client.force_login(self.manager)
        self.assertContains(self.client.get('/'), 'Members')
        self.client.force_login(self.alex_user)
        page = self.client.get('/')
        self.assertContains(page, 'Book a class')
        self.assertNotContains(page, 'Coaches</a>')

    def test_members_and_coaches_cant_open_manager_pages(self):
        for user in (self.alex_user, self.coach_user):
            self.client.force_login(user)
            self.assertEqual(self.client.get('/members/').status_code, 403)
            self.assertEqual(self.client.get('/coaches/').status_code, 403)
            self.assertEqual(self.client.post('/classes/new/').status_code, 403)


class CalendarTests(ClubTestCase):
    def test_events_include_classes_and_pending_requests(self):
        LessonRequest.objects.create(member=self.alex, coach=self.lim, start=soon(3), end=soon(3, 19))
        self.client.force_login(self.manager)

        events = self.client.get('/calendar/events/', self.week()).json()

        titles = sorted(e['title'] for e in events)
        self.assertEqual(titles, ['Junior Foil (0/2)', 'Lesson request: Alex Tan'])

    def test_filters_narrow_the_events(self):
        FencingClass.objects.create(name='Sabre', start=soon(2), end=soon(2, 19), location='Hall B')
        self.client.force_login(self.manager)

        events = self.client.get('/calendar/events/', {**self.week(), 'location': 'Hall B'}).json()

        self.assertEqual([e['title'] for e in events], ['Sabre (0/0)'])

    def test_coaches_see_only_their_classes(self):
        FencingClass.objects.create(name='Other', start=soon(2), end=soon(2, 19))
        self.client.force_login(self.coach_user)

        events = self.client.get('/calendar/events/', self.week()).json()

        self.assertEqual([e['title'] for e in events], ['Junior Foil (0/2)'])

    def test_dragging_moves_a_class(self):
        self.client.force_login(self.manager)
        start, end = soon(4), soon(4, 20)
        response = self.client.post(f'/classes/{self.junior.id}/move/',
                                    {'start': start.isoformat(), 'end': end.isoformat()})
        self.assertEqual(response.status_code, 204)
        self.junior.refresh_from_db()
        self.assertEqual(self.junior.end, end)


class ClassPanelTests(ClubTestCase):
    def test_new_class_returns_its_panel_and_closes_the_dialog(self):
        self.client.force_login(self.manager)
        response = self.client.post('/classes/new/', {
            'name': 'Epee', 'date': soon(5).date(), 'start_time': '18:00', 'end_time': '19:30',
            'coach': self.lim.id,
        }, **HTMX)

        self.assertEqual(response['HX-Retarget'], '#panel')
        self.assertEqual(response['HX-Trigger-After-Swap'], 'closeModal')
        self.assertContains(response, '<h2>Epee</h2>', html=True)
        self.assertEqual(FencingClass.objects.get(name='Epee').coach, self.lim)

    def test_invalid_class_shows_the_dialog_again(self):
        self.client.force_login(self.manager)
        response = self.client.post('/classes/new/', {
            'name': 'Epee', 'date': soon(5).date(), 'start_time': '19:00', 'end_time': '18:00',
        }, **HTMX)
        self.assertNotIn('HX-Retarget', response)
        self.assertContains(response, 'End must be after start.')

    def test_generate_name(self):
        self.client.force_login(self.manager)
        response = self.client.get('/classes/name/', {
            'date': '2026-10-19', 'weapon': 'sabre', 'location': 'Bukit Timah',
        })
        self.assertContains(response, 'value="Monday Sabre BT Class"')

    def test_coach_marks_attendance_on_own_class_only(self):
        row = Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='enrolled')
        other = FencingClass.objects.create(name='Other', start=soon(2), end=soon(2, 19))
        other_row = Attendance.objects.create(fencing_class=other, member=self.alex, status='enrolled')
        self.client.force_login(self.coach_user)

        response = self.client.post(f'/attendance/{row.id}/status/', {'status': 'present'})
        self.assertContains(response, '1 present')
        self.assertEqual(self.client.post(
            f'/attendance/{other_row.id}/status/', {'status': 'present'}
        ).status_code, 403)

    def test_member_enrols_until_the_class_is_full(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.sam, status='enrolled')
        self.client.force_login(self.alex_user)
        self.client.post(f'/classes/{self.junior.id}/enrol/', {'enrolled': '1'})
        self.assertTrue(self.junior.attendance.filter(member=self.alex).exists())

        bea = Member.objects.create(name='Bea')
        self.client.force_login(self.login_for(Profile.Role.MEMBER, member=bea))
        response = self.client.post(f'/classes/{self.junior.id}/enrol/', {'enrolled': '1'})
        self.assertContains(response, 'This class is full.')

    def test_repeat_and_delete_following(self):
        self.client.force_login(self.manager)
        until = (self.junior.start + timedelta(weeks=3)).date()
        response = self.client.post(f'/classes/{self.junior.id}/repeat/', {'until': until})
        self.assertContains(response, 'Added 3 more classes.')

        self.client.post(f'/classes/{self.junior.id}/delete/', {'following': '1'})
        self.assertFalse(FencingClass.objects.filter(name='Junior Foil').exists())


class LessonTests(ClubTestCase):
    def test_member_requests_and_coach_accepts(self):
        self.client.force_login(self.alex_user)
        start = soon(3)
        response = self.client.post(f'/lessons/new/?coach={self.lim.id}', {
            'date': start.date(), 'start_time': '10:00', 'end_time': '11:00', 'note': 'Parries',
        }, **HTMX)
        self.assertEqual(response['HX-Retarget'], '#my-lessons')
        lesson = LessonRequest.objects.get()

        self.client.force_login(self.coach_user)
        response = self.client.post(f'/lesson-requests/{lesson.id}/accept/')
        self.assertContains(response, 'Private lesson: Alex Tan')
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, 'accepted')

    def test_busy_times_say_nothing_about_what(self):
        self.client.force_login(self.alex_user)
        events = self.client.get('/lessons/events/', {**self.week(), 'coach': self.lim.id}).json()
        self.assertEqual([e['title'] for e in events], ['Busy'])

    def test_members_can_only_ask_their_coaches(self):
        stranger = Coach.objects.create(name='Coach Ng')
        self.client.force_login(self.alex_user)
        self.assertEqual(self.client.get(f'/lessons/new/?coach={stranger.id}').status_code, 404)


class MemberTests(ClubTestCase):
    def test_members_page_opens_the_member_in_the_url(self):
        self.client.force_login(self.manager)
        response = self.client.get(f'/members/?member={self.alex.id}')
        self.assertContains(response, 'Edit member')

    def test_member_edits_only_their_own_details(self):
        self.client.force_login(self.alex_user)
        response = self.client.post(f'/members/{self.alex.id}/edit/', {
            'name': 'Alex T', 'email': 'other@example.com', 'phone': '123', 'weapon': 'foil',
        }, **HTMX)
        self.assertEqual(response['HX-Retarget'], '#member-details')
        self.alex.refresh_from_db()
        self.assertEqual((self.alex.name, self.alex.email), ('Alex T', 'alex@example.com'))
        self.assertEqual(self.client.get(f'/members/{self.sam.id}/edit/').status_code, 404)

    def test_switching_a_login_off(self):
        self.client.force_login(self.manager)
        response = self.client.post(f'/logins/{self.alex_user.id}/active/', {'active': '0'})
        self.assertContains(response, 'They can no longer log in')
        self.alex_user.refresh_from_db()
        self.assertFalse(self.alex_user.is_active)
