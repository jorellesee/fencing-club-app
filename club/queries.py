"""What each person can see. Every page asks here rather than filtering on its own,
so a page can't show something these rules hide.

`user` is the logged-in user. Managers see everything, coaches the club's sessions
(their calendar shows only their own), and members only what's theirs.

Lesson requests are unconfirmed sessions in the same table, so `sessions()` leaves
them out and only `requests()` and `lessons()` include them. Start from those
rather than TrainingSession.objects, or a request could show up as if booked.
"""
from datetime import timedelta

from django.db.models import Count, Max, Min, Q
from django.utils import timezone

from .models import Attendance, Coach, Member, TrainingSession
from .roles import COACH, MANAGER, MEMBER, role_of

# The filters a manager can set on the Sessions page.
FILTERS = ['coach', 'member', 'location', 'category', 'weapon', 'size']
# The size filter's choices: by capacity, since 1 makes a session individual.
SIZES = [('group', 'Group'), ('individual', 'Private lessons')]

CONFIRMED = TrainingSession.Status.CONFIRMED
UNCONFIRMED = TrainingSession.Status.UNCONFIRMED
# A session for one person, i.e. a private lesson. See TrainingSession.is_individual.
INDIVIDUAL = Q(capacity=1)


def sessions():
    """Confirmed sessions with their headcounts: `member_count` and `present_count`,
    earliest first. The order_by is needed: Django leaves out the model's default
    ordering when a query counts things."""
    return TrainingSession.objects.filter(status=CONFIRMED).select_related('coach').annotate(
        member_count=Count('attendance'),
        present_count=Count('attendance', filter=Q(attendance__status='present')),
    ).order_by('start')


def lessons():
    """Individual sessions, confirmed or not, with who they're for."""
    return (
        TrainingSession.objects.filter(INDIVIDUAL, coach__isnull=False)
        .select_related('coach').prefetch_related('attendance__member').order_by('start')
    )


def requests():
    """Lessons waiting for their coach to confirm them."""
    return lessons().filter(status=UNCONFIRMED)


def members():
    """Members with their attendance: present out of present + absent, and when
    they were last present."""
    return Member.objects.annotate(
        present_count=Count('attendance', filter=Q(attendance__status='present')),
        marked_count=Count('attendance', filter=Q(attendance__status__in=['present', 'absent'])),
        last_present=Max('attendance__session__start', filter=Q(attendance__status='present')),
    ).select_related('profile__user', 'primary_coach').order_by('name')


def coaches():
    """Coaches with how many sessions they have and when the next one is."""
    confirmed = Q(sessions__status=CONFIRMED)
    return Coach.objects.annotate(
        session_count=Count('sessions', filter=confirmed),
        next_session=Min(
            'sessions__start', filter=confirmed & Q(sessions__start__gte=timezone.now())
        ),
    ).select_related('profile__user').order_by('name')


def locations():
    """Every location used so far, once each, for the filter and the session form."""
    return (
        TrainingSession.objects.exclude(location='')
        .order_by('location')
        .values_list('location', flat=True)
        .distinct()
    )


def own_coach_id(user):
    """A coach login's coach, or 0 (matching nothing) if it isn't linked to one."""
    return user.profile.coach_id or 0


def on_session(**lookup):
    """Sessions with a matching attendance row, e.g. on_session(member=3). A subquery
    rather than a join, so the headcounts stay whole-session."""
    return Q(id__in=Attendance.objects.filter(**lookup).values('session'))


def mine(user):
    """The sessions a member login is on."""
    return on_session(member__profile__user=user)


def bookable():
    """Upcoming group sessions. Private lessons are never open to other members."""
    return Q(start__gt=timezone.now()) & ~INDIVIDUAL


def visible_sessions(user):
    """Sessions this person may open: any for managers and coaches, and for members
    their own or ones they could book."""
    if role_of(user) == MEMBER:
        return sessions().filter(mine(user) | bookable())
    return sessions()


def bookable_sessions(user):
    """Upcoming group sessions a member isn't on yet."""
    return sessions().filter(bookable()).exclude(mine(user))


def scoped(queryset, user, filters):
    """A coach's own, a member's own, or for a manager, everything matching the
    filters."""
    role = role_of(user)
    if role == COACH:
        return queryset.filter(coach=own_coach_id(user))
    if role == MEMBER:
        return queryset.filter(mine(user))
    if filters.get('member'):
        queryset = queryset.filter(on_session(member=filters['member']))
    for field in ['coach', 'location', 'category', 'weapon']:
        if filters.get(field):
            queryset = queryset.filter(**{field: filters[field]})
    if filters.get('size') == 'individual':
        queryset = queryset.filter(INDIVIDUAL)
    elif filters.get('size') == 'group':
        queryset = queryset.exclude(INDIVIDUAL)
    return queryset


def shown_sessions(user, filters):
    """What the calendar and the list show: a manager's filtered sessions, a coach's
    own, a member's own."""
    return scoped(sessions(), user, filters)


def shown_requests(user, filters):
    """Requests for the calendar, beside the sessions from shown_sessions()."""
    return scoped(requests(), user, filters)


def visible_lessons(user):
    """Lessons and requests: all for managers, a coach's own, a member's own."""
    return scoped(lessons(), user, {})


def feed_sessions(user):
    """What someone's calendar feed shows: what their calendar does, with no
    filters, from two months ago onwards."""
    since = timezone.now() - timedelta(days=60)
    return shown_sessions(user, {}).filter(start__gte=since)


def can_edit_session(user, session):
    """Managers edit any confirmed session, coaches only their own sessions' notes
    and attendance. Nobody marks a lesson that hasn't been confirmed."""
    if session.status != CONFIRMED:
        return False
    role = role_of(user)
    if role == MANAGER:
        return True
    return (
        role == COACH and session.coach_id is not None
        and session.coach_id == user.profile.coach_id
    )


def visible_members(user):
    """Members this person may open: all for managers, only themselves for members."""
    if role_of(user) == MEMBER:
        return members().filter(profile__user=user)
    return members()


def history(member):
    """A member's confirmed sessions, newest first."""
    return (
        member.attendance.filter(session__status=CONFIRMED)
        .select_related('session').order_by('-session__start')
    )
