from rest_framework import serializers

from .models import Attendance, FencingClass, Member


class MemberSerializer(serializers.ModelSerializer):
    present_count = serializers.IntegerField(read_only=True)
    marked_count = serializers.IntegerField(read_only=True)
    last_present = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Member
        fields = [
            'id', 'name', 'email', 'phone', 'weapon', 'active',
            'present_count', 'marked_count', 'last_present',
        ]


class FencingClassSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    present_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = FencingClass
        fields = [
            'id', 'name', 'start', 'end', 'coach', 'location', 'weapon', 'capacity', 'notes',
            'member_count', 'present_count', 'series',
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
    coach = serializers.CharField(source='fencing_class.coach', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id', 'fencing_class', 'member', 'member_name', 'class_name', 'class_start',
            'coach', 'status',
        ]


class RepeatSerializer(serializers.Serializer):
    until = serializers.DateField()

