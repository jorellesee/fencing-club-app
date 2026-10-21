from django.contrib import admin

from .models import Attendance, FencingClass, Member

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
    list_display = ['name', 'start', 'end', 'coach', 'capacity', 'present_count']
    list_filter = ['coach']
    search_fields = ['name', 'coach']
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

