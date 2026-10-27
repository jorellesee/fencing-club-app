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
    coach = models.CharField(max_length=100, blank=True)
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
    coach_name = models.CharField(
        max_length=100, blank=True,
        help_text="Coaches only: exactly as typed in a class's coach field.",
    )

    def clean(self):
        if self.role == self.Role.MEMBER and not self.member:
            raise ValidationError({'member': 'Pick the member this login belongs to.'})
        if self.role == self.Role.COACH and not self.coach_name:
            raise ValidationError({'coach_name': 'Enter the coach name used on classes.'})

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'
