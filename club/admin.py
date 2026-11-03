from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from . import queries
from .models import Attendance, Coach, Member, Profile, TrainingSession
from .roles import role_of

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'weapon', 'primary_coach', 'email', 'phone', 'active']
    list_filter = ['weapon', 'primary_coach', 'active']
    search_fields = ['name', 'email']
    autocomplete_fields = ['primary_coach']


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ['name', 'weapon', 'email', 'phone', 'active']
    list_filter = ['weapon', 'active']
    search_fields = ['name', 'email']


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    autocomplete_fields = ['member']


class SizeFilter(admin.SimpleListFilter):
    """Group or individual, which comes from capacity: 1 makes a private lesson."""
    title = 'size'
    parameter_name = 'size'

    def lookups(self, request, model_admin):
        return queries.SIZES

    def queryset(self, request, queryset):
        if self.value() == 'individual':
            return queryset.filter(queries.INDIVIDUAL)
        if self.value() == 'group':
            return queryset.exclude(queries.INDIVIDUAL)
        return queryset


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'start', 'end', 'coach', 'location', 'category', 'status', 'weapon',
        'capacity', 'present_count',
    ]
    list_filter = ['status', SizeFilter, 'category', 'coach', 'location', 'weapon']
    search_fields = ['name', 'coach__name', 'location']
    date_hierarchy = 'start'
    autocomplete_fields = ['coach']
    inlines = [AttendanceInline]

    @admin.display(description='Present')
    def present_count(self, obj):
        return obj.attendance.filter(status='present').count()


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['member', 'session', 'status']
    list_filter = ['status']
    list_editable = ['status']
    autocomplete_fields = ['member', 'session']


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    autocomplete_fields = ['member', 'coach']


# Coaches and members are usually invited from their page in the app. Here,
# tick "Staff status" for a manager, or give a coach or member a profile below.
admin.site.unregister(User)


@admin.register(User)
class ClubUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ['username', 'role', 'is_active']

    @admin.display(description='Role')
    def role(self, user):
        return role_of(user) or '—'
