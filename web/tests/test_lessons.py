from club.models import Coach, Profile, TrainingSession

from .base import HTMX, ClubTestCase, soon


class LessonTests(ClubTestCase):
    def ask(self, hour=10):
        return self.client.post(f'/lessons/new/?coach={self.lim.id}', {
            'date': soon(3).date(), 'start_time': f'{hour}:00', 'end_time': f'{hour + 1}:00',
            'note': 'Parries',
        }, **HTMX)

    def lesson(self):
        return TrainingSession.objects.get(capacity=1)

    def test_member_requests_and_coach_accepts(self):
        self.client.force_login(self.alex_user)
        response = self.ask()
        self.assertEqual(response['HX-Retarget'], '#my-lessons')
        self.assertContains(response, 'unconfirmed until they reply')
        lesson = self.lesson()

        self.client.force_login(self.coach_user)
        response = self.client.post(f'/lesson-requests/{lesson.id}/accept/')
        self.assertContains(response, 'Private lesson: Alex Tan')
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, 'confirmed')

    def test_busy_coach(self):
        self.client.force_login(self.alex_user)
        self.ask()
        self.client.force_login(self.login_for(Profile.Role.MEMBER, member=self.sam))
        self.sam.primary_coach = self.lim
        self.sam.save()
        self.assertContains(self.ask(), 'Coach Lim is busy then.')

    def test_busy_times_say_nothing_about_what(self):
        self.client.force_login(self.alex_user)
        events = self.client.get('/lessons/events/', {**self.week(), 'coach': self.lim.id}).json()
        self.assertEqual([e['title'] for e in events], ['Busy'])

    def test_members_can_only_ask_their_coaches(self):
        stranger = Coach.objects.create(name='Coach Ng')
        self.client.force_login(self.alex_user)
        self.assertEqual(self.client.get(f'/lessons/new/?coach={stranger.id}').status_code, 404)

    def test_only_the_coach_answers_and_only_the_member_cancels(self):
        self.client.force_login(self.alex_user)
        self.ask()
        lesson = self.lesson()
        self.assertEqual(self.client.post(f'/lesson-requests/{lesson.id}/accept/').status_code, 403)

        ng = self.login_for(Profile.Role.COACH, coach=Coach.objects.create(name='Coach Ng'))
        self.client.force_login(ng)
        self.assertEqual(self.client.post(f'/lesson-requests/{lesson.id}/accept/').status_code, 404)

        self.client.force_login(self.coach_user)
        self.assertEqual(self.client.post(f'/lesson-requests/{lesson.id}/cancel/').status_code, 403)

    def test_member_cancels_from_my_requests(self):
        self.client.force_login(self.alex_user)
        self.ask()
        lesson = self.lesson()
        response = self.client.post(f'/lessons/{lesson.id}/cancel/', **HTMX)
        self.assertContains(response, 'Cancelled your lesson')
        self.assertFalse(TrainingSession.objects.filter(id=lesson.id).exists())

    def test_coach_declines(self):
        self.client.force_login(self.alex_user)
        self.ask()
        lesson = self.lesson()
        self.client.force_login(self.coach_user)
        self.client.post(f'/lesson-requests/{lesson.id}/decline/')
        self.assertFalse(TrainingSession.objects.filter(id=lesson.id).exists())

    def test_requests_cannot_be_marked_or_opened_as_sessions(self):
        self.client.force_login(self.alex_user)
        self.ask()
        lesson = self.lesson()
        self.client.force_login(self.coach_user)
        self.assertEqual(self.client.get(f'/sessions/{lesson.id}/').status_code, 404)
        self.assertEqual(self.client.post(f'/sessions/{lesson.id}/notes/').status_code, 404)
        row = lesson.attendance.get()
        self.assertEqual(
            self.client.post(f'/attendance/{row.id}/status/', {'status': 'present'}).status_code,
            403,
        )
