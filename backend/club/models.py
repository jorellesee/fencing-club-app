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
    name = models.CharField(max_length=100)
    start = models.DateTimeField()
    end = models.DateTimeField()
    coach = models.CharField(max_length=100, blank=True)
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
