import json
import uuid
from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Max, Min, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .emails import display_name, send_invite, send_password_reset
from .models import Attendance, Coach, FencingClass, LessonRequest, Member, Profile
from .permissions import COACH, MEMBER, role_of
from .serializers import (
    AttendanceSerializer, CoachSerializer, FencingClassSerializer, InviteSerializer,
    LessonRequestSerializer, LoginSerializer, MemberSerializer, RepeatSerializer,
)


def coaches_class(user, fencing_class):
    """True if this coach login is the coach of `fencing_class`."""
    coach_id = user.profile.coach_id
    return coach_id is not None and fencing_class.coach_id == coach_id


class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    role_actions = {
        COACH: {'list', 'retrieve'},
        MEMBER: {'retrieve', 'partial_update'},
    }
    # Not email, since it's also their login, nor what the club decides.
    role_fields = {MEMBER: {'name', 'phone', 'weapon'}}

    def can_edit(self, user, member):
        profile = getattr(member, 'profile', None)
        return profile is not None and profile.user_id == user.id

    def get_queryset(self):
        queryset = Member.objects.annotate(
            present_count=Count('attendance', filter=Q(attendance__status='present')),
            marked_count=Count(
                'attendance', filter=Q(attendance__status__in=['present', 'absent'])
            ),
            last_present=Max(
                'attendance__fencing_class__start', filter=Q(attendance__status='present')
            ),
        ).select_related('profile__user', 'primary_coach').order_by('name')
        primary_coach = self.request.query_params.get('primary_coach')
        if primary_coach:
            queryset = queryset.filter(primary_coach=primary_coach)
        if role_of(self.request.user) == MEMBER:
            queryset = queryset.filter(profile__user=self.request.user)
        return queryset


class CoachViewSet(viewsets.ModelViewSet):
    serializer_class = CoachSerializer
    # Coaches see the list for the calendar's coach names. Members don't need it.
    role_actions = {COACH: {'list', 'retrieve'}}

    def get_queryset(self):
        return Coach.objects.annotate(
            class_count=Count('classes'),
            next_class=Min('classes__start', filter=Q(classes__start__gte=timezone.now())),
        ).select_related('profile__user')


class FencingClassViewSet(viewsets.ModelViewSet):
    serializer_class = FencingClassSerializer
    role_actions = {
        COACH: {'list', 'retrieve', 'partial_update'},
        MEMBER: {'list', 'retrieve', 'enrol', 'unenrol'},
    }
    role_fields = {COACH: {'notes'}}

    def can_edit(self, user, fencing_class):
        if role_of(user) == MEMBER:
            # enrol and unenrol check everything else themselves.
            return self.action in ('enrol', 'unenrol')
        return coaches_class(user, fencing_class)

    def get_queryset(self):
        queryset = FencingClass.objects.select_related('coach').annotate(
            member_count=Count('attendance'),
            present_count=Count('attendance', filter=Q(attendance__status='present')),
        )
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')
        if start and end:
            queryset = queryset.filter(start__lt=end, end__gt=start)
        coach = self.request.query_params.get('coach')
        if coach:
            queryset = queryset.filter(coach=coach)
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location=location)
        weapon = self.request.query_params.get('weapon')
        if weapon:
            queryset = queryset.filter(weapon=weapon)
        member = self.request.query_params.get('member')
        if member:
            queryset = queryset.filter(attendance__member=member)
        if role_of(self.request.user) == MEMBER:
            queryset = self.member_classes(queryset)
        return queryset

    def member_classes(self, queryset):
        """A member lists their own classes, or with ?bookable=1 the upcoming classes
        they could enrol in. They can open either kind."""
        # A subquery rather than a join, so the headcounts above stay whole-class.
        mine = Q(id__in=Attendance.objects.filter(
            member__profile__user=self.request.user
        ).values('fencing_class'))
        # Private lessons are only ever "mine", never open to other members.
        upcoming = Q(start__gt=timezone.now(), lesson_request__isnull=True)
        if self.action != 'list':
            return queryset.filter(mine | upcoming)
        if self.request.query_params.get('bookable'):
            return queryset.filter(upcoming).exclude(mine)
        return queryset.filter(mine)

    @action(detail=True, methods=['post'])
    def enrol(self, request, pk=None):
        fencing_class = self.get_object()
        member = request.user.profile.member
        if member is None or not member.active:
            raise ValidationError({'detail': 'Your membership isn’t active. Ask a manager.'})
        if fencing_class.start <= timezone.now():
            raise ValidationError({'detail': 'This class has already started.'})
        with transaction.atomic():
            if fencing_class.attendance.filter(member=member).exists():
                raise ValidationError({'detail': 'You’re already on this class.'})
            capacity = fencing_class.capacity
            if capacity is not None and fencing_class.attendance.count() >= capacity:
                raise ValidationError({'detail': 'This class is full.'})
            row = Attendance.objects.create(
                fencing_class=fencing_class, member=member, status='enrolled'
            )
        return Response(AttendanceSerializer(row).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def unenrol(self, request, pk=None):
        fencing_class = self.get_object()
        row = fencing_class.attendance.filter(member__profile__user=request.user).first()
        if row is None:
            raise ValidationError({'detail': 'You’re not on this class.'})
        if fencing_class.start <= timezone.now() or row.status != 'enrolled':
            raise ValidationError(
                {'detail': 'Only upcoming enrolments can be cancelled. Ask a manager.'}
            )
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False)
    def locations(self, request):
        names = (
            FencingClass.objects.exclude(location='')
            .order_by('location')
            .values_list('location', flat=True)
            .distinct()
        )
        return Response(list(names))

    @action(detail=True, methods=['post'])
    def repeat(self, request, pk=None):
        fencing_class = self.get_object()
        serializer = RepeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        until = serializer.validated_data['until']

        if until > timezone.localdate(fencing_class.start) + timedelta(days=366):
            raise ValidationError({'until': 'Repeat for at most one year.'})
        if fencing_class.series and FencingClass.objects.filter(
            series=fencing_class.series, start__gt=fencing_class.start
        ).exists():
            raise ValidationError({'detail': 'Repeat from the last class in the series.'})

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
        return Response({'created': created}, status=status.HTTP_201_CREATED)

    # Times stay per class, and notes are usually about one week.
    SERIES_FIELDS = ['name', 'coach', 'location', 'weapon', 'capacity']

    @action(detail=True, methods=['post'], url_path='update-following')
    def update_following(self, request, pk=None):
        fencing_class = self.get_object()
        if fencing_class.series is None:
            raise ValidationError({'detail': 'This class is not part of a series.'})
        data = {key: value for key, value in request.data.items() if key in self.SERIES_FIELDS}
        serializer = self.get_serializer(fencing_class, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        following = FencingClass.objects.filter(
            series=fencing_class.series, start__gte=fencing_class.start
        )
        return Response({'updated': following.update(**serializer.validated_data)})

    @action(detail=True, methods=['post'], url_path='delete-following')
    def delete_following(self, request, pk=None):
        fencing_class = self.get_object()
        if fencing_class.series is None:
            raise ValidationError({'detail': 'This class is not part of a series.'})
        following = FencingClass.objects.filter(
            series=fencing_class.series, start__gte=fencing_class.start
        )
        count = following.count()
        following.delete()
        return Response({'deleted': count})


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    role_actions = {
        COACH: {'list', 'retrieve', 'partial_update', 'unmarked'},
        MEMBER: {'list', 'retrieve'},
    }
    role_fields = {COACH: {'status'}}

    def can_edit(self, user, row):
        return coaches_class(user, row.fencing_class)

    def get_queryset(self):
        queryset = Attendance.objects.select_related('member', 'fencing_class').order_by(
            'member__name'
        )
        fencing_class = self.request.query_params.get('fencing_class')
        if fencing_class:
            queryset = queryset.filter(fencing_class=fencing_class)
        member = self.request.query_params.get('member')
        if member:
            queryset = queryset.filter(member=member).order_by('-fencing_class__start')
        if role_of(self.request.user) == MEMBER:
            queryset = queryset.filter(member__profile__user=self.request.user)
        return queryset

    @action(detail=False)
    def unmarked(self, request):
        rows = self.get_queryset().filter(
            status='enrolled', fencing_class__end__lt=timezone.now()
        ).order_by('fencing_class__start', 'fencing_class', 'member__name')
        if role_of(request.user) == COACH:
            coach_id = request.user.profile.coach_id
            rows = rows.filter(fencing_class__coach=coach_id) if coach_id else rows.none()
        return Response(self.get_serializer(rows, many=True).data)


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


class LessonRequestViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    """Members request private lessons. The coach, or a manager, accepts or declines."""

    serializer_class = LessonRequestSerializer
    role_actions = {
        COACH: {'list', 'accept', 'decline'},
        MEMBER: {'list', 'create', 'cancel', 'coaches', 'busy'},
    }
    role_fields = {MEMBER: {'coach', 'start', 'end', 'note'}}

    def can_edit(self, user, lesson):
        role = role_of(user)
        if role == COACH:
            return self.action in ('accept', 'decline') and lesson.coach_id == user.profile.coach_id
        if role == MEMBER:
            return self.action == 'cancel'
        return False

    def get_queryset(self):
        queryset = LessonRequest.objects.select_related('member', 'coach')
        role = role_of(self.request.user)
        if role == COACH:
            coach_id = self.request.user.profile.coach_id
            queryset = queryset.filter(coach=coach_id) if coach_id else queryset.none()
        elif role == MEMBER:
            queryset = queryset.filter(member__profile__user=self.request.user)
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        # The same filters as classes, so the calendar can show requests beside them.
        if params.get('start') and params.get('end'):
            queryset = queryset.filter(start__lt=params['end'], end__gt=params['start'])
        if params.get('coach'):
            queryset = queryset.filter(coach=params['coach'])
        if params.get('member'):
            queryset = queryset.filter(member=params['member'])
        return queryset

    def own_member(self):
        member = self.request.user.profile.member
        if member is None or not member.active:
            raise ValidationError({'detail': 'Your membership isn’t active. Ask a manager.'})
        return member

    def perform_create(self, serializer):
        if role_of(self.request.user) != MEMBER:
            raise ValidationError({'detail': 'Only members can request lessons.'})
        member = self.own_member()
        data = serializer.validated_data
        if not coaches_of(member).filter(id=data['coach'].id).exists():
            raise ValidationError({'coach': 'You can only ask your own coaches.'})
        with transaction.atomic():
            classes, pending = coach_bookings(data['coach'], data['start'], data['end'])
            if classes.exists() or pending.exists():
                raise ValidationError({'detail': f'{data["coach"].name} is busy then.'})
            serializer.save(member=member)

    @action(detail=False)
    def coaches(self, request):
        """Just names, so members don't see coaches' contact details."""
        coaches = coaches_of(self.own_member())
        return Response([{'id': coach.id, 'name': coach.name} for coach in coaches])

    @action(detail=False)
    def busy(self, request):
        """When one of the member's coaches is booked, without saying what with."""
        member = self.own_member()
        coach = coaches_of(member).filter(id=request.query_params.get('coach')).first()
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        if coach is None or not (start and end):
            raise ValidationError({'detail': 'Choose one of your coaches and a date range.'})
        classes, pending = coach_bookings(coach, start, end)
        # The member's own requests and lessons come from list() instead, with details.
        classes = classes.exclude(lesson_request__member=member)
        pending = pending.exclude(member=member)
        slots = [*classes.values('start', 'end'), *pending.values('start', 'end')]
        return Response(sorted(slots, key=lambda slot: slot['start']))

    def pending_lesson(self):
        lesson = self.get_object()
        if lesson.status != LessonRequest.Status.PENDING:
            raise ValidationError({'detail': f'This request is already {lesson.status}.'})
        return lesson

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        lesson = self.pending_lesson()
        with transaction.atomic():
            if FencingClass.objects.filter(
                coach=lesson.coach, start__lt=lesson.end, end__gt=lesson.start
            ).exists():
                raise ValidationError({'detail': 'There’s already a class at that time.'})
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
        return Response(self.get_serializer(lesson).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        lesson = self.pending_lesson()
        lesson.status = LessonRequest.Status.DECLINED
        lesson.save(update_fields=['status'])
        return Response(self.get_serializer(lesson).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        lesson = self.get_object()
        if lesson.status not in (LessonRequest.Status.PENDING, LessonRequest.Status.ACCEPTED):
            raise ValidationError({'detail': f'This request is already {lesson.status}.'})
        if lesson.start <= timezone.now():
            raise ValidationError({'detail': 'This lesson has already started.'})
        with transaction.atomic():
            if lesson.fencing_class:
                lesson.fencing_class.delete()
                lesson.fencing_class = None
            lesson.status = LessonRequest.Status.CANCELLED
            lesson.save(update_fields=['fencing_class', 'status'])
        return Response(self.get_serializer(lesson).data)


class LoginViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Coach and member logins. Managers only, since no `role_actions` are listed.
    Managers invite people here, resend invites, and switch logins off with is_active."""

    serializer_class = LoginSerializer
    queryset = (
        User.objects.filter(profile__isnull=False)
        .select_related('profile__member', 'profile__coach')
        .order_by('profile__role', 'username')
    )

    def create(self, request):
        invite = InviteSerializer(data=request.data)
        invite.is_valid(raise_exception=True)
        data = invite.validated_data

        if data['role'] == MEMBER:
            existing = Profile.objects.filter(member=data['member']).first()
        else:
            existing = Profile.objects.filter(coach=data['coach']).first()
        if existing:
            # Inviting someone again just resends their email.
            return self.send_again(existing.user)

        email = data['email']
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise ValidationError({'email': 'Another login already uses this email address.'})

        with transaction.atomic():
            # No password until they choose one from the email's link.
            user = User(username=email, email=email)
            user.set_unusable_password()
            user.save()
            Profile.objects.create(
                user=user,
                role=data['role'],
                member=data.get('member'),
                coach=data.get('coach'),
            )
            # Inside the transaction, so if the email fails nothing is left half made.
            send_invite(user)
        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        return self.send_again(self.get_object())

    def send_again(self, user):
        if not user.is_active:
            raise ValidationError({'detail': f'{display_name(user)}’s login is switched off.'})
        if user.has_usable_password():
            raise ValidationError({'detail': f'{display_name(user)} has already set a password.'})
        # A new unusable password changes the hash, so links in older emails stop working.
        user.set_unusable_password()
        user.save(update_fields=['password'])
        send_invite(user)
        return Response(self.get_serializer(user).data)


def too_many_attempts(scope, key, limit, period=15 * 60):
    """Counts attempts at `scope` for `key`, e.g. logins as one username. True once
    there have been more than `limit` of them within `period` seconds."""
    cache_key = f'attempts:{scope}:{key}'
    cache.add(cache_key, 0, period)
    return cache.incr(cache_key) > limit


def account(user):
    """What the frontend needs to know about who is logged in, or None."""
    role = role_of(user)
    if role is None:
        return None
    profile = getattr(user, 'profile', None)
    return {
        'username': user.get_username(),
        'role': role,
        'member': profile.member_id if role == MEMBER else None,
        'coach': profile.coach_id if role == COACH else None,
    }


# Plain Django views, not DRF, so CsrfViewMiddleware checks the login form too.
@ensure_csrf_cookie
def me(request):
    return JsonResponse(account(request.user), safe=False)


@require_POST
def login_view(request):
    data = json.loads(request.body or '{}')
    username = (data.get('username') or '').strip()
    if '@' in username:
        # Invited logins use their email as the username, but older ones may not.
        match = User.objects.filter(email__iexact=username).first()
        if match:
            username = match.get_username()
    if too_many_attempts('login', username.lower(), limit=10):
        return JsonResponse({'detail': 'Too many attempts. Try again in 15 minutes.'}, status=429)
    user = authenticate(request, username=username, password=data.get('password'))
    if user is None or account(user) is None:
        return JsonResponse({'detail': 'Wrong username or password.'}, status=400)
    login(request, user)
    return JsonResponse(account(user))


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse(None, safe=False)


@require_POST
def password_reset_view(request):
    email = (json.loads(request.body or '{}').get('email') or '').strip()
    if email and not too_many_attempts('reset', email.lower(), limit=3):
        for user in User.objects.filter(email__iexact=email, is_active=True):
            if account(user) is not None:
                send_password_reset(user)
    # The same answer either way, so nobody can use this to find out who has a login.
    return JsonResponse({'detail': 'If that email has a login, we’ve sent it a link.'})


def user_from_link(uidb64, token):
    """The user an invite or reset link is for, or None if it's expired or used."""
    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, DjangoValidationError):
        return None
    if user.is_active and default_token_generator.check_token(user, token):
        return user
    return None


@ensure_csrf_cookie
@require_http_methods(['GET', 'POST'])
def set_password_view(request, uidb64, token):
    """GET checks the link before showing the form. POST sets the password and logs in."""
    user = user_from_link(uidb64, token)
    if user is None:
        return JsonResponse(
            {'detail': 'This link has expired or has already been used.'}, status=400
        )
    if request.method == 'GET':
        return JsonResponse({
            'username': user.get_username(),
            'name': display_name(user),
            'invited': not user.has_usable_password(),
        })

    data = json.loads(request.body or '{}')
    form = SetPasswordForm(user, {
        'new_password1': data.get('password'),
        'new_password2': data.get('password_again'),
    })
    if not form.is_valid():
        messages = [message for errors in form.errors.values() for message in errors]
        return JsonResponse({'detail': ' '.join(messages)}, status=400)
    form.save()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse(account(user))
