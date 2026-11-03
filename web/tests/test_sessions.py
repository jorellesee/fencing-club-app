from datetime import timedelta

from django.utils import timezone

from club import services
from club.models import Attendance, Member, Profile, TrainingSession

from .base import HTMX, ClubTestCase, soon


class CalendarTests(ClubTestCase):
    def events(self, **filters):
        return self.client.get('/calendar/events/', {**self.week(), **filters}).json()

    def test_events_include_sessions_and_requests(self):
        services.request_lesson(self.alex_user, self.lim, soon(3), soon(3, 19))
        self.client.force_login(self.manager)
        titles = sorted(e['title'] for e in self.events())
        self.assertEqual(titles, ['Junior Foil (0/2)', 'Lesson request: Alex Tan'])

    def test_filters_narrow_the_events(self):
        TrainingSession.objects.create(name='Sabre', start=soon(2), end=soon(2, 19), location='Hall B')
        self.client.force_login(self.manager)
        self.assertEqual([e['title'] for e in self.events(location='Hall B')], ['Sabre (0/0)'])

    def test_size_filter(self):
        TrainingSession.objects.create(name='Solo', start=soon(2), end=soon(2, 19), capacity=1)
        self.client.force_login(self.manager)
        self.assertEqual([e['title'] for e in self.events(size='individual')], ['Solo (0/1)'])
        self.assertNotIn('Solo (0/1)', [e['title'] for e in self.events(size='group')])

    def test_coaches_see_only_their_sessions(self):
        TrainingSession.objects.create(name='Other', start=soon(2), end=soon(2, 19))
        self.client.force_login(self.coach_user)
        self.assertEqual([e['title'] for e in self.events()], ['Junior Foil (0/2)'])

    def test_dragging_moves_a_session(self):
        self.client.force_login(self.manager)
        start, end = soon(4), soon(4, 20)
        response = self.client.post(f'/sessions/{self.junior.id}/move/',
                                    {'start': start.isoformat(), 'end': end.isoformat()})
        self.assertEqual(response.status_code, 204)
        self.junior.refresh_from_db()
        self.assertEqual(self.junior.end, end)

    def test_a_session_cannot_end_before_it_starts(self):
        self.client.force_login(self.manager)
        response = self.client.post(f'/sessions/{self.junior.id}/move/', {
            'start': soon(4, 20).isoformat(), 'end': soon(4).isoformat(),
        })
        self.assertEqual(response.status_code, 400)

    def test_list_shows_a_members_own_status(self):
        Attendance.objects.create(session=self.junior, member=self.alex, status='excused')
        self.client.force_login(self.alex_user)
        self.assertContains(self.client.get('/table/'), 'status-excused')


# What the dialog's selects post when left as they are.
GROUP_FENCING = {'category': 'fencing'}


class SessionFormTests(ClubTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.manager)

    def test_new_session_returns_its_panel_and_closes_the_dialog(self):
        response = self.client.post('/sessions/new/', {
            'name': 'Epee', 'date': soon(5).date(), 'start_time': '18:00', 'end_time': '19:30',
            'coach': self.lim.id, **GROUP_FENCING,
        }, **HTMX)
        self.assertEqual(response['HX-Retarget'], '#panel')
        self.assertEqual(response['HX-Trigger-After-Swap'], 'closeModal')
        self.assertContains(response, '<h2>Epee</h2>', html=True)
        self.assertEqual(TrainingSession.objects.get(name='Epee').coach, self.lim)

    def test_invalid_session_shows_the_dialog_again(self):
        response = self.client.post('/sessions/new/', {
            'name': 'Epee', 'date': soon(5).date(), 'start_time': '19:00', 'end_time': '18:00',
        }, **HTMX)
        self.assertNotIn('HX-Retarget', response)
        self.assertContains(response, 'End must be after start.')

    def test_generate_name(self):
        response = self.client.get('/sessions/name/', {
            'date': '2026-10-19', 'weapon': 'sabre', 'location': 'Bukit Timah',
        })
        self.assertContains(response, 'value="Monday Sabre BT Class"')

    def test_generate_name_for_conditioning(self):
        response = self.client.get('/sessions/name/', {
            'date': '2026-10-23', 'category': 'conditioning', 'weapon': 'sabre',
            'location': 'Bukit Timah',
        })
        self.assertContains(response, 'value="Friday BT Conditioning"')

    def test_new_conditioning_session(self):
        self.client.post('/sessions/new/', {
            'name': 'Strength', 'date': soon(5).date(), 'start_time': '07:00',
            'end_time': '08:00', 'category': 'conditioning',
        }, **HTMX)
        self.assertEqual(TrainingSession.objects.get(name='Strength').category, 'conditioning')
        self.assertContains(self.client.get('/table/'), 'Physical conditioning')

    def test_editing_this_and_following_sessions(self):
        self.client.post(f'/sessions/{self.junior.id}/repeat/',
                         {'until': (self.junior.start + timedelta(weeks=2)).date()})
        second = TrainingSession.objects.order_by('start')[1]
        self.client.post(f'/sessions/{second.id}/edit/', {
            'name': 'Renamed', 'date': second.start.date(), 'start_time': '09:00',
            'end_time': '10:00', 'apply_to_following': 'on', **GROUP_FENCING,
        })
        names = list(TrainingSession.objects.order_by('start').values_list('name', flat=True))
        self.assertEqual(names, ['Junior Foil', 'Renamed', 'Renamed'])
        # Times are only ever changed on the one session.
        third = TrainingSession.objects.order_by('start')[2]
        self.assertEqual(timezone.localtime(third.start).hour, 18)

    def test_repeat_and_delete_following(self):
        until = (self.junior.start + timedelta(weeks=3)).date()
        response = self.client.post(f'/sessions/{self.junior.id}/repeat/', {'until': until})
        self.assertContains(response, 'Added 3 more sessions.')
        self.client.post(f'/sessions/{self.junior.id}/delete/', {'following': '1'})
        self.assertFalse(TrainingSession.objects.exists())


class PanelTests(ClubTestCase):
    def test_adding_and_removing_members(self):
        self.client.force_login(self.manager)
        response = self.client.post(f'/sessions/{self.junior.id}/add/', {'member': self.sam.id})
        self.assertContains(response, 'Sam Lee')
        row = self.junior.attendance.get()
        self.client.post(f'/attendance/{row.id}/remove/')
        self.assertFalse(self.junior.attendance.exists())

    def test_coach_marks_attendance_and_notes_on_own_session_only(self):
        row = Attendance.objects.create(session=self.junior, member=self.alex, status='enrolled')
        other = TrainingSession.objects.create(name='Other', start=soon(2), end=soon(2, 19))
        other_row = Attendance.objects.create(session=other, member=self.alex, status='enrolled')
        self.client.force_login(self.coach_user)

        self.assertContains(self.client.post(f'/attendance/{row.id}/status/', {'status': 'present'}),
                            '1 present')
        self.assertEqual(self.client.post(f'/sessions/{self.junior.id}/notes/', {'notes': 'Masks'})
                         .status_code, 204)
        refused = [
            self.client.post(f'/attendance/{other_row.id}/status/', {'status': 'present'}),
            self.client.post(f'/sessions/{other.id}/notes/', {'notes': 'Hi'}),
        ]
        self.assertEqual([r.status_code for r in refused], [403, 403])

    def test_coaches_cannot_change_sessions_or_rosters(self):
        self.client.force_login(self.coach_user)
        responses = [
            self.client.post('/sessions/new/', {'name': 'New'}),
            self.client.post(f'/sessions/{self.junior.id}/edit/', {'name': 'New'}),
            self.client.post(f'/sessions/{self.junior.id}/move/', {}),
            self.client.post(f'/sessions/{self.junior.id}/repeat/', {'until': '2027-01-01'}),
            self.client.post(f'/sessions/{self.junior.id}/delete/'),
            self.client.post(f'/sessions/{self.junior.id}/add/', {'member': self.sam.id}),
        ]
        self.assertEqual({r.status_code for r in responses}, {403})

    def test_members_see_only_their_own_row_and_cannot_mark(self):
        row = Attendance.objects.create(session=self.junior, member=self.alex, status='enrolled')
        Attendance.objects.create(session=self.junior, member=self.sam, status='enrolled')
        self.client.force_login(self.alex_user)
        response = self.client.get(f'/sessions/{self.junior.id}/')
        self.assertContains(response, 'Alex Tan')
        self.assertNotContains(response, 'Sam Lee')
        self.assertEqual(self.client.post(f'/attendance/{row.id}/status/', {'status': 'present'})
                         .status_code, 403)

    def test_member_enrols_until_the_session_is_full(self):
        Attendance.objects.create(session=self.junior, member=self.sam, status='enrolled')
        self.client.force_login(self.alex_user)
        self.client.post(f'/sessions/{self.junior.id}/enrol/', {'enrolled': '1'})
        self.assertTrue(self.junior.attendance.filter(member=self.alex).exists())

        bea = Member.objects.create(name='Bea')
        self.client.force_login(self.login_for(Profile.Role.MEMBER, member=bea))
        response = self.client.post(f'/sessions/{self.junior.id}/enrol/', {'enrolled': '1'})
        self.assertContains(response, 'This session is full.')

    def test_member_cancels_an_enrolment(self):
        Attendance.objects.create(session=self.junior, member=self.alex, status='enrolled')
        self.client.force_login(self.alex_user)
        self.client.post(f'/sessions/{self.junior.id}/enrol/', {'enrolled': '0'})
        self.assertFalse(self.junior.attendance.exists())

    def test_members_cannot_open_other_members_past_sessions(self):
        past = TrainingSession.objects.create(name='Past', start=soon(-3), end=soon(-3, 19))
        self.client.force_login(self.alex_user)
        self.assertEqual(self.client.get(f'/sessions/{past.id}/').status_code, 404)

    def test_coaches_cannot_enrol(self):
        self.client.force_login(self.coach_user)
        self.assertEqual(self.client.post(f'/sessions/{self.junior.id}/enrol/').status_code, 403)


class BookTests(ClubTestCase):
    def test_booking_removes_the_session_from_the_list(self):
        self.client.force_login(self.alex_user)
        row = '<td class="strong">Junior Foil</td>'
        self.assertContains(self.client.get('/book/'), row, html=True)
        response = self.client.post(f'/book/{self.junior.id}/', **HTMX)
        self.assertContains(response, 'You’re enrolled in Junior Foil')
        self.assertNotContains(response, row, html=True)
