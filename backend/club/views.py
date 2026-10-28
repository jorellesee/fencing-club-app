import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Max, Min, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from . import services
from .emails import display_name, send_password_reset, user_from_link
from .models import Attendance, Coach, FencingClass, LessonRequest, Member
from .permissions import COACH, MEMBER, role_of
from .serializers import (
    AttendanceSerializer, CoachSerializer, FencingClassSerializer, InviteSerializer,
    LessonRequestSerializer, LoginSerializer, MemberSerializer, RepeatSerializer,
)


def exception_handler(exc, context):
    """Turns the ValidationErrors from club/services.py into 400 responses, like
    DRF's own: {"detail": "..."}, or {"field": "..."} for one field."""
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, 'error_dict'):
            detail = {field: ' '.join(messages) for field, messages in exc.message_dict.items()}
        else:
            detail = {'detail': ' '.join(exc.messages)}
        exc = ValidationError(detail)
    return drf_exception_handler(exc, context)


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
        row = services.enrol(services.own_member(request.user), fencing_class)
        return Response(AttendanceSerializer(row).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def unenrol(self, request, pk=None):
        services.unenrol(request.user, self.get_object())
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
        created = services.repeat_weekly(fencing_class, serializer.validated_data['until'])
        return Response({'created': created}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='update-following')
    def update_following(self, request, pk=None):
        fencing_class = self.get_object()
        following = services.following(fencing_class)
        data = {
            key: value for key, value in request.data.items() if key in services.SERIES_FIELDS
        }
        serializer = self.get_serializer(fencing_class, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response({'updated': following.update(**serializer.validated_data)})

    @action(detail=True, methods=['post'], url_path='delete-following')
    def delete_following(self, request, pk=None):
        following = services.following(self.get_object())
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

    def perform_create(self, serializer):
        serializer.instance = services.request_lesson(self.request.user, **serializer.validated_data)

    @action(detail=False)
    def coaches(self, request):
        """Just names, so members don't see coaches' contact details."""
        coaches = services.coaches_of(services.own_member(request.user))
        return Response([{'id': coach.id, 'name': coach.name} for coach in coaches])

    @action(detail=False)
    def busy(self, request):
        """When one of the member's coaches is booked, without saying what with."""
        member = services.own_member(request.user)
        coach = services.coaches_of(member).filter(id=request.query_params.get('coach')).first()
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        if coach is None or not (start and end):
            raise ValidationError({'detail': 'Choose one of your coaches and a date range.'})
        return Response(services.busy_slots(member, coach, start, end))

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        lesson = self.get_object()
        services.accept_lesson(lesson)
        return Response(self.get_serializer(lesson).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        lesson = self.get_object()
        services.decline_lesson(lesson)
        return Response(self.get_serializer(lesson).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        lesson = self.get_object()
        services.cancel_lesson(lesson)
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
        user, created = services.invite(**invite.validated_data)
        return Response(
            self.get_serializer(user).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        user = services.send_again(self.get_object())
        return Response(self.get_serializer(user).data)


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
    username = services.username_for(data.get('username'))
    if services.too_many_attempts('login', username.lower(), limit=10):
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
    if email and not services.too_many_attempts('reset', email.lower(), limit=3):
        for user in User.objects.filter(email__iexact=email, is_active=True):
            if account(user) is not None:
                send_password_reset(user)
    # The same answer either way, so nobody can use this to find out who has a login.
    return JsonResponse({'detail': 'If that email has a login, we’ve sent it a link.'})


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
