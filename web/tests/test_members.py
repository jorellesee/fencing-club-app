from club.models import Coach

from .base import HTMX, ClubTestCase


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
            for url in ['/members/', '/coaches/', f'/members/{self.alex.id}/',
                        f'/coaches/{self.lim.id}/', '/members/new/', '/coaches/new/']:
                self.assertEqual(self.client.get(url).status_code, 403, url)


class MemberTests(ClubTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.manager)

    def test_members_page_opens_the_member_in_the_url(self):
        self.assertContains(self.client.get(f'/members/?member={self.alex.id}'), 'Edit member')

    def test_adding_a_member_opens_them(self):
        response = self.client.post('/members/new/', {'name': 'Bea', 'active': 'on'}, **HTMX)
        self.assertEqual(response['HX-Retarget'], '#panel')
        self.assertIn('?member=', response['HX-Push-Url'])

    def test_a_member_needs_a_name(self):
        response = self.client.post('/members/new/', {'name': ''}, **HTMX)
        self.assertContains(response, 'This field is required.')

    def test_editing_a_member(self):
        self.client.post(f'/members/{self.sam.id}/edit/', {
            'name': 'Sam Lee', 'phone': '9123 4567', 'primary_coach': self.lim.id,
        }, **HTMX)
        self.sam.refresh_from_db()
        self.assertEqual((self.sam.phone, self.sam.primary_coach, self.sam.active),
                         ('9123 4567', self.lim, False))

    def test_switching_a_login_off(self):
        response = self.client.post(f'/logins/{self.alex_user.id}/active/', {'active': '0'})
        self.assertContains(response, 'They can no longer log in')
        self.alex_user.refresh_from_db()
        self.assertFalse(self.alex_user.is_active)


class OwnDetailsTests(ClubTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.alex_user)

    def test_member_sees_their_profile(self):
        self.assertContains(self.client.get('/profile/'), 'Edit my details')

    def test_member_edits_only_name_phone_and_weapon(self):
        response = self.client.post(f'/members/{self.alex.id}/edit/', {
            'name': 'Alex T', 'email': 'other@example.com', 'phone': '123', 'weapon': 'foil',
            'active': '', 'primary_coach': '',
        }, **HTMX)
        self.assertEqual(response['HX-Retarget'], '#member-details')
        self.alex.refresh_from_db()
        self.assertEqual(
            (self.alex.name, self.alex.email, self.alex.active, self.alex.primary_coach),
            ('Alex T', 'alex@example.com', True, self.lim),
        )

    def test_member_cannot_edit_others(self):
        self.assertEqual(self.client.get(f'/members/{self.sam.id}/edit/').status_code, 404)


class CoachTests(ClubTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.manager)

    def test_coach_page(self):
        response = self.client.get(f'/coaches/{self.lim.id}/')
        self.assertContains(response, 'Alex Tan')  # a member they coach
        self.assertContains(response, 'Junior Foil')  # an upcoming class

    def test_adding_a_coach_refreshes_the_page(self):
        response = self.client.post('/coaches/new/', {'name': 'Coach Ng', 'active': 'on'}, **HTMX)
        self.assertEqual(response['HX-Refresh'], 'true')
        self.assertTrue(Coach.objects.filter(name='Coach Ng').exists())

    def test_coach_names_are_unique(self):
        response = self.client.post('/coaches/new/', {'name': 'Coach Lim'}, **HTMX)
        self.assertContains(response, 'already exists')
