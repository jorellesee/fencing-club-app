"""The club's rules, shared by the JSON API (club/views.py) and the htmx pages (web/views.py).

Each function raises Django's ValidationError when a rule says no, with a message
that can be shown to the person as it is.
"""
import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .emails import display_name, send_invite
from .models import Attendance, Coach, FencingClass, LessonRequest, Profile
from .permissions import MEMBER, role_of


def own_member(user):
    """The member a member login belongs to, if their membership is active."""
    member = user.profile.member
    if member is None or not member.active:
        raise ValidationError('Your membership isn’t active. Ask a manager.')
    return member


# Classes

def enrol(member, fencing_class):
    if fencing_class.start <= timezone.now():
        raise ValidationError('This class has already started.')
    with transaction.atomic():
        if fencing_class.attendance.filter(member=member).exists():
            raise ValidationError('You’re already on this class.')
        capacity = fencing_class.capacity
        if capacity is not None and fencing_class.attendance.count() >= capacity:
            raise ValidationError('This class is full.')
        return Attendance.objects.create(
            fencing_class=fencing_class, member=member, status='enrolled'
        )


def unenrol(user, fencing_class):
    row = fencing_class.attendance.filter(member__profile__user=user).first()
    if row is None:
        raise ValidationError('You’re not on this class.')
    if fencing_class.start <= timezone.now() or row.status != 'enrolled':
        raise ValidationError('Only upcoming enrolments can be cancelled. Ask a manager.')
    row.delete()


def repeat_weekly(fencing_class, until):
    """Copies the class, and its roster, every week up to `until`. Returns how many."""
    if until > timezone.localdate(fencing_class.start) + timedelta(days=366):
        raise ValidationError({'until': 'Repeat for at most one year.'})
    if fencing_class.series and FencingClass.objects.filter(
        series=fencing_class.series, start__gt=fencing_class.start
    ).exists():
        raise ValidationError('Repeat from the last class in the series.')

    roster = list(fencing_class.attendance.values_list('member_id', flat=True))
    created = 0
    with transaction.atomic():
        if fencing_class.series is None:
            fencing_class.series = uuid.uuid4()
            fencing_class.save(update_fields=['series'])
        week = 1
        while timezone.localdate(fencing_class.start + timedelta(weeks=week)) <= until:
            copy = FencingClass.objects.create(
                name=fencing_class.name,
                start=fencing_class.start + timedelta(weeks=week),
                end=fencing_class.end + timedelta(weeks=week),
                coach=fencing_class.coach,
                location=fencing_class.location,
                weapon=fencing_class.weapon,
                capacity=fencing_class.capacity,
                notes=fencing_class.notes,
                series=fencing_class.series,
            )
            Attendance.objects.bulk_create([
                Attendance(fencing_class=copy, member_id=member_id, status='enrolled')
                for member_id in roster
            ])
            created += 1
            week += 1
    return created


# Times stay per class, and notes are usually about one week.
SERIES_FIELDS = ['name', 'coach', 'location', 'weapon', 'capacity']


def following(fencing_class):
    """This class and the later ones in its weekly series."""
    if fencing_class.series is None:
        raise ValidationError('This class is not part of a series.')
    return FencingClass.objects.filter(
        series=fencing_class.series, start__gte=fencing_class.start
    )


# Private lessons

def coaches_of(member):
    """The coaches a member can ask for lessons: their primary coach, and whoever
    coaches a class they're on."""
    return Coach.objects.filter(
        Q(members=member) | Q(classes__attendance__member=member), active=True
    ).distinct()


def coach_bookings(coach, start, end):
    """The coach's classes and pending lesson requests overlapping start to end.
    Accepted lessons are classes already, so they're in the first list."""
    classes = FencingClass.objects.filter(coach=coach, start__lt=end, end__gt=start)
    pending = LessonRequest.objects.filter(
        coach=coach, status=LessonRequest.Status.PENDING, start__lt=end, end__gt=start
    )
    return classes, pending


def busy_slots(member, coach, start, end):
    """When one of the member's coaches is booked, without saying what with."""
    classes, pending = coach_bookings(coach, start, end)
    # The member's own requests and lessons are shown with their details instead.
    classes = classes.exclude(lesson_request__member=member)
    pending = pending.exclude(member=member)
    slots = [*classes.values('start', 'end'), *pending.values('start', 'end')]
    return sorted(slots, key=lambda slot: slot['start'])


def lesson_time_errors(start, end):
    """What's wrong with a lesson from start to end, by field, or {} if nothing."""
    if end <= start:
        return {'end': 'End must be after start.'}
    if start <= timezone.now():
        return {'start': 'Choose a time in the future.'}
    if end - start > timedelta(hours=3):
        return {'end': 'A lesson can be at most 3 hours.'}
    return {}


def request_lesson(user, coach, start, end, note=''):
    if role_of(user) != MEMBER:
        raise ValidationError('Only members can request lessons.')
    member = own_member(user)
    if not coaches_of(member).filter(id=coach.id).exists():
        raise ValidationError({'coach': 'You can only ask your own coaches.'})
    with transaction.atomic():
        classes, pending = coach_bookings(coach, start, end)
        if classes.exists() or pending.exists():
            raise ValidationError(f'{coach.name} is busy then.')
        return LessonRequest.objects.create(
            member=member, coach=coach, start=start, end=end, note=note
        )


def check_pending(lesson):
    if lesson.status != LessonRequest.Status.PENDING:
        raise ValidationError(f'This request is already {lesson.status}.')


def accept_lesson(lesson):
    """Makes the lesson a one-person class, so it shows on calendars and can be marked."""
    check_pending(lesson)
    with transaction.atomic():
        if FencingClass.objects.filter(
            coach=lesson.coach, start__lt=lesson.end, end__gt=lesson.start
        ).exists():
            raise ValidationError('There’s already a class at that time.')
        fencing_class = FencingClass.objects.create(
            name=f'Private lesson: {lesson.member.name}',
            start=lesson.start,
            end=lesson.end,
            coach=lesson.coach,
            weapon=lesson.member.weapon,
            capacity=1,
            notes=lesson.note,
        )
        Attendance.objects.create(
            fencing_class=fencing_class, member=lesson.member, status='enrolled'
        )
        lesson.fencing_class = fencing_class
        lesson.status = LessonRequest.Status.ACCEPTED
        lesson.save(update_fields=['fencing_class', 'status'])


def decline_lesson(lesson):
    check_pending(lesson)
    lesson.status = LessonRequest.Status.DECLINED
    lesson.save(update_fields=['status'])


def cancel_lesson(lesson):
    if lesson.status not in (LessonRequest.Status.PENDING, LessonRequest.Status.ACCEPTED):
        raise ValidationError(f'This request is already {lesson.status}.')
    if lesson.start <= timezone.now():
        raise ValidationError('This lesson has already started.')
    with transaction.atomic():
        if lesson.fencing_class:
            lesson.fencing_class.delete()
            lesson.fencing_class = None
        lesson.status = LessonRequest.Status.CANCELLED
        lesson.save(update_fields=['fencing_class', 'status'])


# Logins

def invite(member=None, coach=None):
    """Gives a member or coach a login and emails them a link to choose a password.
    Inviting someone again just resends their email. Returns (user, created)."""
    if member:
        key, role, person = 'member', Profile.Role.MEMBER, member
    elif coach:
        key, role, person = 'coach', Profile.Role.COACH, coach
    else:
        raise ValidationError('Choose a member or a coach to invite.')
    if not person.email:
        raise ValidationError({key: f'Add an email address to this {key} first.'})

    existing = Profile.objects.filter(**{key: person}).first()
    if existing:
        return send_again(existing.user), False

    email = person.email.strip().lower()
    if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
        raise ValidationError({'email': 'Another login already uses this email address.'})

    with transaction.atomic():
        # No password until they choose one from the email's link.
        user = User(username=email, email=email)
        user.set_unusable_password()
        user.save()
        Profile.objects.create(user=user, role=role, member=member, coach=coach)
        # Inside the transaction, so if the email fails nothing is left half made.
        send_invite(user)
    return user, True


def send_again(user):
    if not user.is_active:
        raise ValidationError(f'{display_name(user)}’s login is switched off.')
    if user.has_usable_password():
        raise ValidationError(f'{display_name(user)} has already set a password.')
    # A new unusable password changes the hash, so links in older emails stop working.
    user.set_unusable_password()
    user.save(update_fields=['password'])
    send_invite(user)
    return user


def too_many_attempts(scope, key, limit, period=15 * 60):
    """Counts attempts at `scope` for `key`, e.g. logins as one username. True once
    there have been more than `limit` of them within `period` seconds."""
    cache_key = f'attempts:{scope}:{key}'
    cache.add(cache_key, 0, period)
    return cache.incr(cache_key) > limit


def username_for(typed):
    """Invited logins use their email as the username, but older ones may not."""
    typed = (typed or '').strip()
    if '@' in typed:
        match = User.objects.filter(email__iexact=typed).first()
        if match:
            return match.get_username()
    return typed


def error_text(error):
    """A ValidationError as one line, for showing at the top of a form."""
    return ' '.join(error.messages)
