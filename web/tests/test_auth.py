import re

from django.contrib.auth.models import User
from django.core import mail

from club.models import Coach

from .base import HTMX, ClubTestCase


def emailed_link():
    return re.search(r'(/set-password/\S+)', mail.outbox[-1].body).group(1)


class LoginTests(ClubTestCase):
    def log_in(self, username, password='en-garde-123'):
        return self.client.post('/login/', {'username': username, 'password': password})

    def test_pages_send_logged_out_people_to_login(self):
        self.assertRedirects(self.client.get('/members/'), '/login/?next=/members/')

    def test_htmx_requests_redirect_the_whole_page(self):
        response = self.client.get(f'/classes/{self.junior.id}/', **HTMX)
        self.assertEqual(response['HX-Redirect'], '/login/')

    def test_logging_in_then_out(self):
        self.assertRedirects(self.log_in(self.alex_user.username), '/')
        self.client.post('/logout/')
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_logging_in_with_email(self):
        self.alex_user.email = 'alex@example.com'
        self.alex_user.save()
        self.assertRedirects(self.log_in('ALEX@example.com'), '/')

    def test_next_only_goes_to_this_site(self):
        response = self.client.post('/login/?next=//evil.example.com/', {
            'username': self.alex_user.username, 'password': 'en-garde-123',
        })
        self.assertRedirects(response, '/')

    def test_wrong_password(self):
        self.assertContains(self.log_in(self.alex_user.username, 'x'), 'Wrong username or password.')

    def test_logins_without_a_role_are_refused(self):
        User.objects.create_user('nobody', password='en-garde-123')
        self.assertContains(self.log_in('nobody'), 'Wrong username or password.')

    def test_too_many_attempts(self):
        for _ in range(10):
            self.log_in(self.alex_user.username, 'x')
        self.assertContains(self.log_in(self.alex_user.username), 'Too many attempts.')

    def test_switched_off_logins_cannot_log_in(self):
        self.client.force_login(self.manager)
        self.client.post(f'/logins/{self.alex_user.id}/active/', {'active': '0'})
        self.client.logout()
        self.assertContains(self.log_in(self.alex_user.username), 'Wrong username or password.')


class InviteTests(ClubTestCase):
    def setUp(self):
        super().setUp()
        self.ng = Coach.objects.create(name='Coach Ng', email='ng@example.com')
        self.passwords = {'new_password1': 'a-long-passphrase', 'new_password2': 'a-long-passphrase'}

    def test_invite_link_sets_password_and_logs_in(self):
        self.client.force_login(self.manager)
        response = self.client.post(f'/members/{self.sam.id}/invite/')
        self.assertContains(response, 'Add an email address')
        self.sam.email = 'sam@example.com'
        self.sam.save()
        self.assertContains(self.client.post(f'/members/{self.sam.id}/invite/'),
                            'Sent to sam@example.com')
        self.client.logout()

        link = emailed_link()
        self.assertContains(self.client.get(link), 'Welcome, Sam Lee')
        self.assertRedirects(self.client.post(link, self.passwords), '/')
        self.assertContains(self.client.get('/book/'), 'Book a class')

    def test_links_work_once_and_resending_replaces_them(self):
        self.client.force_login(self.manager)
        self.client.post(f'/coaches/{self.ng.id}/invite/')
        old = emailed_link()
        self.assertContains(self.client.post(f'/coaches/{self.ng.id}/invite/'), 'Resend invite')
        self.assertEqual(self.client.get(old).status_code, 400)
        new = emailed_link()
        self.assertEqual(self.client.post(new, self.passwords).status_code, 302)
        self.assertEqual(self.client.get(new).status_code, 400)

    def test_weak_passwords_are_refused(self):
        self.client.force_login(self.manager)
        self.client.post(f'/coaches/{self.ng.id}/invite/')
        response = self.client.post(emailed_link(), {'new_password1': '123', 'new_password2': '123'})
        self.assertContains(response, 'too short')

    def test_only_managers_can_invite(self):
        for user in (self.coach_user, self.alex_user):
            self.client.force_login(user)
            self.assertEqual(self.client.post(f'/coaches/{self.lim.id}/invite/').status_code, 403)

    def test_bad_link(self):
        self.assertEqual(self.client.get('/set-password/xx/not-a-token/').status_code, 400)


class PasswordResetTests(ClubTestCase):
    def test_reset_emails_a_working_link(self):
        self.alex_user.email = 'alex@example.com'
        self.alex_user.save()
        self.client.post('/forgot-password/', {'email': 'ALEX@example.com'})
        response = self.client.get(emailed_link())
        self.assertContains(response, 'Choose a new password')

    def test_unknown_email_gets_the_same_answer(self):
        User.objects.create_user('nobody', email='nobody@example.com')  # no role either
        response = self.client.post('/forgot-password/', {'email': 'nobody@example.com'})
        self.assertContains(response, 'If that email has a login')
        self.assertEqual(len(mail.outbox), 0)
