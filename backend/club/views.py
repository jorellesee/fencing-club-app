import json
import uuid
from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Attendance, FencingClass, Member
from .permissions import COACH, MEMBER, role_of
from .serializers import (
    AttendanceSerializer, FencingClassSerializer, MemberSerializer, RepeatSerializer,
)


class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    role_actions = {
        COACH: {'list', 'retrieve'},
        MEMBER: {'retrieve'},
    }

    def get_queryset(self):
        queryset = Member.objects.annotate(
            present_count=Count('attendance', filter=Q(attendance__status='present')),
            marked_count=Count(
                'attendance', filter=Q(attendance__status__in=['present', 'absent'])
            ),
            last_present=Max(
                'attendance__fencing_class__start', filter=Q(attendance__status='present')
            ),
        ).order_by('name')
        if role_of(self.request.user) == MEMBER:
            queryset = queryset.filter(profile__user=self.request.user)
        return queryset


class FencingClassViewSet(viewsets.ModelViewSet):
    serializer_class = FencingClassSerializer
    role_actions = {
        COACH: {'list', 'retrieve', 'partial_update', 'coaches'},
        MEMBER: {'list', 'retrieve'},
    }
    role_fields = {COACH: {'notes'}}

    def can_edit(self, user, fencing_class):
        return fencing_class.coach == user.profile.coach_name

    def get_queryset(self):
        queryset = FencingClass.objects.annotate(
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
            queryset = queryset.filter(attendance__member__profile__user=self.request.user)
        return queryset

    @action(detail=False)
    def coaches(self, request):
        names = (
            FencingClass.objects.exclude(coach='')
            .order_by('coach')
            .values_list('coach', flat=True)
            .distinct()
        )
        return Response(list(names))

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
        return row.fencing_class.coach == user.profile.coach_name

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
            rows = rows.filter(fencing_class__coach=request.user.profile.coach_name)
        return Response(self.get_serializer(rows, many=True).data)


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
        'coach_name': profile.coach_name if role == COACH else '',
    }


# Plain Django views, not DRF, so CsrfViewMiddleware checks the login form too.
@ensure_csrf_cookie
def me(request):
    return JsonResponse(account(request.user), safe=False)


@require_POST
def login_view(request):
    data = json.loads(request.body or '{}')
    user = authenticate(request, username=data.get('username'), password=data.get('password'))
    if user is None or account(user) is None:
        return JsonResponse({'detail': 'Wrong username or password.'}, status=400)
    login(request, user)
    return JsonResponse(account(user))


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse(None, safe=False)
