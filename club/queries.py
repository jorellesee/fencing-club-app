"""What each person can see. Every page asks here rather than filtering on its own,
so a page can't show something these rules hide.

`user` is the logged-in user. Managers see everything, coaches the club's classes
(their calendar shows only their own), and members only what's theirs.
"""
from django.db.models import Count, Max, Min, Q
from django.utils import timezone

from .models import Attendance, Coach, FencingClass, LessonRequest, Member
from .roles import COACH, MANAGER, MEMBER, role_of

# The filters a manager can set on the Classes page.
FILTERS = ['coach', 'member', 'location', 'weapon']


def classes():
    """Classes with their headcounts: `member_count` and `present_count`."""
    return FencingClass.objects.select_related('coach').annotate(
        member_count=Count('attendance'),
        present_count=Count('attendance', filter=Q(attendance__status='present')),
    )


def members():
    """Members with their attendance: present out of present + absent, and when
    they were last present."""
    return Member.objects.annotate(
        present_count=Count('attendance', filter=Q(attendance__status='present')),
        marked_count=Count('attendance', filter=Q(attendance__status__in=['present', 'absent'])),
        last_present=Max(
            'attendance__fencing_class__start', filter=Q(attendance__status='present')
        ),
    ).select_related('profile__user', 'primary_coach').order_by('name')


def coaches():
    """Coaches with how many classes they have and when the next one is."""
    return Coach.objects.annotate(
        class_count=Count('classes'),
        next_class=Min('classes__start', filter=Q(classes__start__gte=timezone.now())),
    ).select_related('profile__user')


def locations():
    """Every location used so far, once each, for the filter and the class form."""
    return (
        FencingClass.objects.exclude(location='')
        .order_by('location')
        .values_list('location', flat=True)
        .distinct()
    )


def own_coach_id(user):
    """A coach login's coach, or 0 (matching nothing) if it isn't linked to one."""
    return user.profile.coach_id or 0


def on_class(**lookup):
    """Classes with a matching attendance row, e.g. on_class(member=3). A subquery
    rather than a join, so the headcounts stay whole-class."""
    return Q(id__in=Attendance.objects.filter(**lookup).values('fencing_class'))


def mine(user):
    """The classes a member login is on."""
    return on_class(member__profile__user=user)


def bookable():
    """Upcoming classes. Private lessons are never open to other members."""
    return Q(start__gt=timezone.now(), lesson_request__isnull=True)


def visible_classes(user):
    """Classes this person may open: any for managers and coaches, and for members
    their own or ones they could book."""
    if role_of(user) == MEMBER:
        return classes().filter(mine(user) | bookable())
    return classes()


def bookable_classes(user):
    """Upcoming classes a member isn't on yet."""
    return classes().filter(bookable()).exclude(mine(user))


def shown_classes(user, filters):
    """What the calendar and the list show: a manager's filtered classes, a coach's
    own, a member's own."""
    role = role_of(user)
    queryset = classes()
    if role == COACH:
        return queryset.filter(coach=own_coach_id(user))
    if role == MEMBER:
        return queryset.filter(mine(user))
    if filters.get('coach'):
        queryset = queryset.filter(coach=filters['coach'])
    if filters.get('member'):
        queryset = queryset.filter(on_class(member=filters['member']))
    if filters.get('location'):
        queryset = queryset.filter(location=filters['location'])
    if filters.get('weapon'):
        queryset = queryset.filter(weapon=filters['weapon'])
    return queryset


def can_edit_class(user, fencing_class):
    """Managers edit anything, coaches only their own classes' notes and attendance."""
    role = role_of(user)
    if role == MANAGER:
        return True
    return (
        role == COACH and fencing_class.coach_id is not None
        and fencing_class.coach_id == user.profile.coach_id
    )


def visible_requests(user):
    """Lesson requests: all for managers, a coach's own, a member's own."""
    queryset = LessonRequest.objects.select_related('member', 'coach')
    role = role_of(user)
    if role == COACH:
        return queryset.filter(coach=own_coach_id(user))
    if role == MEMBER:
        return queryset.filter(member__profile__user=user)
    return queryset


def shown_requests(user, filters):
    """Pending requests for the calendar, beside the classes from shown_classes()."""
    queryset = visible_requests(user).filter(status=LessonRequest.Status.PENDING)
    if role_of(user) != MANAGER:
        return queryset
    # Requests have no location or weapon, so those filters hide them.
    if filters.get('location') or filters.get('weapon'):
        return queryset.none()
    if filters.get('coach'):
        queryset = queryset.filter(coach=filters['coach'])
    if filters.get('member'):
        queryset = queryset.filter(member=filters['member'])
    return queryset


def visible_members(user):
    """Members this person may open: all for managers, only themselves for members."""
    if role_of(user) == MEMBER:
        return members().filter(profile__user=user)
    return members()


def history(member):
    """A member's classes, newest first."""
    return member.attendance.select_related('fencing_class').order_by('-fencing_class__start')
