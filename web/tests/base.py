from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from club.models import Coach, Member, Profile, TrainingSession

# What htmx sends with every request it makes.
HTMX = {'HTTP_HX_REQUEST': 'true'}


def soon(days, hour=18):
    """A time `days` from now, on the hour, in the club's time zone."""
    day = timezone.localtime() + timedelta(days=days)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)


class ClubTestCase(TestCase):
    """A manager, Coach Lim with a login, Alex (Lim's member, with a login), Sam
    (no login), and an upcoming class of Lim's with room for two."""

    def setUp(self):
        cache.clear()  # login attempt counts
        self.manager = User.objects.create_user('manager', is_staff=True)
        self.lim = Coach.objects.create(name='Coach Lim', email='lim@example.com')
        self.alex = Member.objects.create(
            name='Alex Tan', email='alex@example.com', primary_coach=self.lim
        )
        self.sam = Member.objects.create(name='Sam Lee')
        self.junior = TrainingSession.objects.create(
            name='Junior Foil', start=soon(2), end=soon(2, 19), coach=self.lim, capacity=2
        )
        self.coach_user = self.login_for(Profile.Role.COACH, coach=self.lim)
        self.alex_user = self.login_for(Profile.Role.MEMBER, member=self.alex)

    def login_for(self, role, **person):
        user = User.objects.create_user(f'{role}-{User.objects.count()}', password='en-garde-123')
        Profile.objects.create(user=user, role=role, **person)
        return user

    def week(self):
        start = timezone.now() - timedelta(days=1)
        return {'start': start.isoformat(), 'end': (start + timedelta(days=7)).isoformat()}
