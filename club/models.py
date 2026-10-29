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


class FencingClass(models.Model):
    class Weapon(models.TextChoices):
        FOIL = 'foil', 'Foil'
        EPEE = 'epee', 'Épée'
        SABRE = 'sabre', 'Sabre'
        MIXED = 'mixed', 'Mixed'

    name = models.CharField(max_length=100)
    start = models.DateTimeField()
    end = models.DateTimeField()
    coach = models.ForeignKey(
        Coach, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes'
    )
    location = models.CharField(max_length=100, blank=True)
    weapon = models.CharField(max_length=10, choices=Weapon.choices, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    series = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['start']
        verbose_name_plural = 'fencing classes'

    def __str__(self):
        return f'{self.name} ({self.start:%a %d %b %H:%M})'

class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'
        ENROLLED = 'enrolled', 'Enrolled'
        EXCUSED = 'excused', 'Excused'

    fencing_class = models.ForeignKey(
        FencingClass, on_delete=models.CASCADE, related_name='attendance'
    )
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name='attendance'
    )
    status = models.CharField(max_length=10, choices=Status.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['fencing_class', 'member'],
                name='one_attendance_per_member_per_class',
            )
        ]

    def __str__(self):
        return f'{self.member} – {self.fencing_class}: {self.status}'


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
        help_text='Coaches only: whose classes this login can mark.',
    )

    def clean(self):
        if self.role == self.Role.MEMBER and not self.member:
            raise ValidationError({'member': 'Pick the member this login belongs to.'})
        if self.role == self.Role.COACH and not self.coach:
            raise ValidationError({'coach': 'Pick the coach this login belongs to.'})

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'


class LessonRequest(models.Model):
    """A member asking one of their coaches for a private lesson. Accepting it
    makes a one-person FencingClass, so it shows on calendars and can be marked."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        CANCELLED = 'cancelled', 'Cancelled'

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='lesson_requests')
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, related_name='lesson_requests')
    start = models.DateTimeField()
    end = models.DateTimeField()
    note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    fencing_class = models.OneToOneField(
        FencingClass, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lesson_request',
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start']

    def __str__(self):
        return f'{self.member} with {self.coach} ({self.start:%a %d %b %H:%M}): {self.status}'


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
