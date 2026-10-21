import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Attendance, FencingClass, Member
from .serializers import (
    AttendanceSerializer, FencingClassSerializer, MemberSerializer, RepeatSerializer,
)


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.order_by('name')
    serializer_class = MemberSerializer


class FencingClassViewSet(viewsets.ModelViewSet):
    serializer_class = FencingClassSerializer

    def get_queryset(self):
        queryset = FencingClass.objects.annotate(
            member_count=Count('attendance'),
            present_count=Count('attendance', filter=Q(attendance__status='present')),
        )
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')
        if start and end:
            queryset = queryset.filter(start__lt=end, end__gt=start)
        return queryset

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

    def get_queryset(self):
        queryset = Attendance.objects.select_related('member').order_by('member__name')
        fencing_class = self.request.query_params.get('fencing_class')
        if fencing_class:
            queryset = queryset.filter(fencing_class=fencing_class)
        return queryset
