from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Attendance, FencingClass, Member, Profile
from .permissions import role_of

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'weapon', 'email', 'phone', 'active']
    list_filter = ['weapon', 'active']
    search_fields = ['name', 'email']
class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    autocomplete_fields = ['member']


@admin.register(FencingClass)
class FencingClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'start', 'end', 'coach', 'location', 'capacity', 'present_count']
    list_filter = ['coach', 'location']
    search_fields = ['name', 'coach', 'location']
    date_hierarchy = 'start'
    inlines = [AttendanceInline]

    @admin.display(description='Present')
    def present_count(self, obj):
        return obj.attendance.filter(status='present').count()


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['member', 'fencing_class', 'status']
    list_filter = ['status']
    list_editable = ['status']
    autocomplete_fields = ['member', 'fencing_class']


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    autocomplete_fields = ['member']


# Logins are created here: tick "Staff status" for a manager, or give a coach
# or member a profile below.
admin.site.unregister(User)


@admin.register(User)
class ClubUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ['username', 'role', 'is_active']

    @admin.display(description='Role')
    def role(self, user):
        return role_of(user) or '—'
