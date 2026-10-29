from club.models import Coach, LessonRequest, Profile

from .base import HTMX, ClubTestCase, soon


class LessonTests(ClubTestCase):
    def ask(self, hour=10):
        return self.client.post(f'/lessons/new/?coach={self.lim.id}', {
            'date': soon(3).date(), 'start_time': f'{hour}:00', 'end_time': f'{hour + 1}:00',
            'note': 'Parries',
        }, **HTMX)

    def test_member_requests_and_coach_accepts(self):
        self.client.force_login(self.alex_user)
        response = self.ask()
        self.assertEqual(response['HX-Retarget'], '#my-lessons')
        self.assertContains(response, 'pending until they reply')
        lesson = LessonRequest.objects.get()

        self.client.force_login(self.coach_user)
        response = self.client.post(f'/lesson-requests/{lesson.id}/accept/')
        self.assertContains(response, 'Private lesson: Alex Tan')
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, 'accepted')

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
        lesson = LessonRequest.objects.get()
        self.assertEqual(self.client.post(f'/lesson-requests/{lesson.id}/accept/').status_code, 403)

        ng = self.login_for(Profile.Role.COACH, coach=Coach.objects.create(name='Coach Ng'))
        self.client.force_login(ng)
        self.assertEqual(self.client.post(f'/lesson-requests/{lesson.id}/accept/').status_code, 404)

        self.client.force_login(self.coach_user)
        self.assertEqual(self.client.post(f'/lesson-requests/{lesson.id}/cancel/').status_code, 403)

    def test_member_cancels_from_my_requests(self):
        self.client.force_login(self.alex_user)
        self.ask()
        lesson = LessonRequest.objects.get()
        response = self.client.post(f'/lessons/{lesson.id}/cancel/', **HTMX)
        self.assertContains(response, 'Cancelled your lesson')
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, 'cancelled')
