import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Member(models.Model):
    class Weapon(models.TextChoices):
        FOIL = 'foil', 'Foil'
        EPEE = 'epee', 'Épée'
        SABRE = 'sabre', 'Sabre'

    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    weapon = models.CharField(max_length=10, choices=Weapon.choices, blank=True)
    active = models.BooleanField(default=True)
    primary_coach = models.ForeignKey(
        'Coach', on_delete=models.SET_NULL, null=True, blank=True, related_name='members'
    )

    def __str__(self):
        return self.name

class Coach(models.Model):
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    weapon = models.CharField(max_length=10, choices=Member.Weapon.choices, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'coaches'

    def __str__(self):
        return self.name


class TrainingSession(models.Model):
    """Anything on the club's timetable: a group class, a private lesson, physical
    conditioning. A capacity of 1 makes it individual, i.e. a private lesson. A
    member asking for one makes an unconfirmed individual session, with them on
    it, which their coach then confirms."""

    class Weapon(models.TextChoices):
        FOIL = 'foil', 'Foil'
        EPEE = 'epee', 'Épée'
        SABRE = 'sabre', 'Sabre'
        MIXED = 'mixed', 'Mixed'

    class Category(models.TextChoices):
        FENCING = 'fencing', 'Fencing'
        CONDITIONING = 'conditioning', 'Physical conditioning'

    class Status(models.TextChoices):
        UNCONFIRMED = 'unconfirmed', 'Unconfirmed'
        CONFIRMED = 'confirmed', 'Confirmed'

    name = models.CharField(max_length=100)
    start = models.DateTimeField()
    end = models.DateTimeField()
    coach = models.ForeignKey(
        Coach, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions'
    )
    location = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.FENCING)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CONFIRMED)
    weapon = models.CharField(max_length=10, choices=Weapon.choices, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    series = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['start']

    def __str__(self):
        return f'{self.name} ({self.start:%a %d %b %H:%M})'

    @property
    def is_individual(self):
        return self.capacity == 1

    @property
    def member(self):
        """Who an individual session is for, or None for a group. Prefetch
        `attendance__member` when listing them, or this is a query each."""
        if not self.is_individual:
            return None
        rows = self.attendance.all()
        return rows[0].member if rows else None

class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'
        ENROLLED = 'enrolled', 'Enrolled'
        EXCUSED = 'excused', 'Excused'

    session = models.ForeignKey(
        TrainingSession, on_delete=models.CASCADE, related_name='attendance'
    )
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name='attendance'
    )
    status = models.CharField(max_length=10, choices=Status.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'member'],
                name='one_attendance_per_member_per_session',
            )
        ]

    def __str__(self):
        return f'{self.member} – {self.session}: {self.status}'


class Profile(models.Model):
    """Gives a coach or member login its role. Managers are staff users and need none."""

    class Role(models.TextChoices):
        COACH = 'coach', 'Coach'
        MEMBER = 'member', 'Member'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    member = models.OneToOneField(
        Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='profile',
        help_text='Members only: whose schedule and history this login sees.',
    )
    coach = models.OneToOneField(
        Coach, on_delete=models.SET_NULL, null=True, blank=True, related_name='profile',
        help_text='Coaches only: whose sessions this login can mark.',
    )

    def clean(self):
        if self.role == self.Role.MEMBER and not self.member:
            raise ValidationError({'member': 'Pick the member this login belongs to.'})
        if self.role == self.Role.COACH and not self.coach:
            raise ValidationError({'coach': 'Pick the coach this login belongs to.'})

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'


def new_feed_token():
    return secrets.token_urlsafe(32)


class CalendarFeed(models.Model):
    """The secret in someone's calendar feed URL. Google Calendar fetches the feed
    without logging in, so knowing the token is what lets it in. Resetting it gives
    a new URL, and the old one stops working."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calendar_feed'
    )
    token = models.CharField(max_length=64, unique=True, default=new_feed_token)

    def reset(self):
        self.token = new_feed_token()
        self.save(update_fields=['token'])

    def __str__(self):
        return f'Calendar feed for {self.user}'
