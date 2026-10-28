from django.contrib.auth.models import User
from rest_framework import serializers

from .emails import display_name
from .models import Attendance, Coach, FencingClass, LessonRequest, Member
from .services import lesson_time_errors


def login_status(user):
    """'invited' until the password is set, then 'active' or 'deactivated'."""
    if not user.is_active:
        return 'deactivated'
    return 'active' if user.has_usable_password() else 'invited'


def login_of(person):
    """A member's or coach's login and its status, or None if they haven't been invited."""
    profile = getattr(person, 'profile', None)
    if profile is None:
        return None
    return {'id': profile.user_id, 'status': login_status(profile.user)}


class MemberSerializer(serializers.ModelSerializer):
    primary_coach_name = serializers.CharField(
        source='primary_coach.name', read_only=True, default=''
    )
    present_count = serializers.IntegerField(read_only=True)
    marked_count = serializers.IntegerField(read_only=True)
    last_present = serializers.DateTimeField(read_only=True)
    login = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            'id', 'name', 'email', 'phone', 'weapon', 'active', 'primary_coach',
            'primary_coach_name', 'present_count', 'marked_count', 'last_present', 'login',
        ]

    def get_login(self, member):
        return login_of(member)


class CoachSerializer(serializers.ModelSerializer):
    class_count = serializers.IntegerField(read_only=True)
    next_class = serializers.DateTimeField(read_only=True)
    login = serializers.SerializerMethodField()

    class Meta:
        model = Coach
        fields = [
            'id', 'name', 'email', 'phone', 'weapon', 'active', 'class_count', 'next_class',
            'login',
        ]

    def get_login(self, coach):
        return login_of(coach)


class LoginSerializer(serializers.ModelSerializer):
    """A coach's or member's login, for the manager's Logins page."""

    role = serializers.CharField(source='profile.role', read_only=True)
    name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'name', 'status', 'is_active']
        read_only_fields = ['username', 'email']

    def get_name(self, user):
        return display_name(user)

    def get_status(self, user):
        return login_status(user)


class InviteSerializer(serializers.Serializer):
    """A member or a coach. services.invite checks they have an email address."""

    member = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all(), required=False)
    coach = serializers.PrimaryKeyRelatedField(queryset=Coach.objects.all(), required=False)


class FencingClassSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source='coach.name', read_only=True, default='')
    member_count = serializers.IntegerField(read_only=True)
    present_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = FencingClass
        fields = [
            'id', 'name', 'start', 'end', 'coach', 'coach_name', 'location', 'weapon',
            'capacity', 'notes', 'member_count', 'present_count', 'series',
        ]
        read_only_fields = ['series']

    def validate(self, data):
        start = data.get('start', getattr(self.instance, 'start', None))
        end = data.get('end', getattr(self.instance, 'end', None))
        if end <= start:
            raise serializers.ValidationError({'end': 'End must be after start.'})
        return data


class AttendanceSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    class_name = serializers.CharField(source='fencing_class.name', read_only=True)
    class_start = serializers.DateTimeField(source='fencing_class.start', read_only=True)
    coach = serializers.IntegerField(source='fencing_class.coach_id', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id', 'fencing_class', 'member', 'member_name', 'class_name', 'class_start',
            'coach', 'status',
        ]


class LessonRequestSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    coach_name = serializers.CharField(source='coach.name', read_only=True)

    class Meta:
        model = LessonRequest
        fields = [
            'id', 'member', 'member_name', 'coach', 'coach_name', 'start', 'end', 'note',
            'status', 'fencing_class',
        ]
        read_only_fields = ['member', 'status', 'fencing_class']

    def validate(self, data):
        errors = lesson_time_errors(data['start'], data['end'])
        if errors:
            raise serializers.ValidationError(errors)
        return data


class RepeatSerializer(serializers.Serializer):
    until = serializers.DateField()

