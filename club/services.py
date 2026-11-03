"""The club's rules: what happens when someone enrols, repeats a session, asks for
a lesson and so on. The pages in web/ call these, and nothing here knows about HTTP.

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
from .models import Attendance, Coach, Profile, TrainingSession
from .roles import MEMBER, role_of

CONFIRMED = TrainingSession.Status.CONFIRMED
UNCONFIRMED = TrainingSession.Status.UNCONFIRMED


def own_member(user):
    """The member a member login belongs to, if their membership is active."""
    member = user.profile.member
    if member is None or not member.active:
        raise ValidationError('Your membership isn’t active. Ask a manager.')
    return member


# Sessions

def enrol(member, session):
    if session.start <= timezone.now():
        raise ValidationError('This session has already started.')
    with transaction.atomic():
        if session.attendance.filter(member=member).exists():
            raise ValidationError('You’re already on this session.')
        capacity = session.capacity
        if capacity is not None and session.attendance.count() >= capacity:
            raise ValidationError('This session is full.')
        return Attendance.objects.create(
            session=session, member=member, status='enrolled'
        )


def unenrol(user, session):
    if session.is_individual:
        raise ValidationError('Cancel a private lesson from Private lessons.')
    row = session.attendance.filter(member__profile__user=user).first()
    if row is None:
        raise ValidationError('You’re not on this session.')
    if session.start <= timezone.now() or row.status != 'enrolled':
        raise ValidationError('Only upcoming enrolments can be cancelled. Ask a manager.')
    row.delete()


def repeat_weekly(session, until):
    """Copies the session, and its roster, every week up to `until`. Returns how many."""
    if until > timezone.localdate(session.start) + timedelta(days=366):
        raise ValidationError({'until': 'Repeat for at most one year.'})
    if session.series and TrainingSession.objects.filter(
        series=session.series, start__gt=session.start
    ).exists():
        raise ValidationError('Repeat from the last session in the series.')

    roster = list(session.attendance.values_list('member_id', flat=True))
    created = 0
    with transaction.atomic():
        if session.series is None:
            session.series = uuid.uuid4()
            session.save(update_fields=['series'])
        week = 1
        while timezone.localdate(session.start + timedelta(weeks=week)) <= until:
            copy = TrainingSession.objects.create(
                name=session.name,
                start=session.start + timedelta(weeks=week),
                end=session.end + timedelta(weeks=week),
                coach=session.coach,
                location=session.location,
                category=session.category,
                weapon=session.weapon,
                capacity=session.capacity,
                notes=session.notes,
                series=session.series,
            )
            Attendance.objects.bulk_create([
                Attendance(session=copy, member_id=member_id, status='enrolled')
                for member_id in roster
            ])
            created += 1
            week += 1
    return created


# Times stay per session, and notes are usually about one week.
SERIES_FIELDS = ['name', 'category', 'coach', 'location', 'weapon', 'capacity']


def following(session):
    """This session and the later ones in its weekly series."""
    if session.series is None:
        raise ValidationError('This session is not part of a series.')
    return TrainingSession.objects.filter(
        series=session.series, start__gte=session.start
    )


# Private lessons: individual sessions a member asks for, unconfirmed until their
# coach says yes. Declining or cancelling one deletes it.

def coaches_of(member):
    """The coaches a member can ask for lessons: their primary coach, and whoever
    coaches a session they're on."""
    return Coach.objects.filter(
        Q(members=member)
        | Q(sessions__status=CONFIRMED, sessions__attendance__member=member),
        active=True,
    ).distinct()


def coach_bookings(coach, start, end):
    """The coach's sessions overlapping start to end, including unconfirmed lessons,
    since the time is held for them until the coach answers."""
    return TrainingSession.objects.filter(coach=coach, start__lt=end, end__gt=start)


def busy_slots(member, coach, start, end):
    """When one of the member's coaches is booked, without saying what with."""
    # The member's own requests and lessons are shown with their details instead.
    bookings = coach_bookings(coach, start, end).exclude(attendance__member=member)
    return list(bookings.order_by('start').values('start', 'end'))


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
    """An unconfirmed individual session with the member on it, for the coach to
    confirm or decline."""
    if role_of(user) != MEMBER:
        raise ValidationError('Only members can request lessons.')
    member = own_member(user)
    if not coaches_of(member).filter(id=coach.id).exists():
        raise ValidationError({'coach': 'You can only ask your own coaches.'})
    with transaction.atomic():
        if coach_bookings(coach, start, end).exists():
            raise ValidationError(f'{coach.name} is busy then.')
        lesson = TrainingSession.objects.create(
            name=f'Private lesson: {member.name}',
            start=start,
            end=end,
            coach=coach,
            weapon=member.weapon,
            capacity=1,
            notes=note,
            status=UNCONFIRMED,
        )
        Attendance.objects.create(session=lesson, member=member, status='enrolled')
    return lesson


def check_unconfirmed(lesson):
    if not lesson.is_individual or lesson.status != UNCONFIRMED:
        raise ValidationError('This lesson is already confirmed.')


def accept_lesson(lesson):
    """Confirms the lesson, so it shows on calendars and can be marked."""
    check_unconfirmed(lesson)
    with transaction.atomic():
        clash = coach_bookings(lesson.coach, lesson.start, lesson.end).filter(status=CONFIRMED)
        if clash.exists():
            raise ValidationError('There’s already a session at that time.')
        lesson.status = CONFIRMED
        lesson.save(update_fields=['status'])


def decline_lesson(lesson):
    check_unconfirmed(lesson)
    lesson.delete()


def cancel_lesson(lesson):
    """The member calls off a request, or a confirmed lesson that hasn't started."""
    if not lesson.is_individual:
        raise ValidationError('Only private lessons can be cancelled here.')
    if lesson.start <= timezone.now():
        raise ValidationError('This lesson has already started.')
    lesson.delete()


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
