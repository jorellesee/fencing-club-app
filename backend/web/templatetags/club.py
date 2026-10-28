from django import template
from django.utils.html import format_html

from club.models import FencingClass, LessonRequest

register = template.Library()

WEAPONS = dict(FencingClass.Weapon.choices)
ATTENDANCE = ['enrolled', 'present', 'absent', 'excused']
LOGIN_LABELS = {'invited': 'Invited', 'active': 'Active', 'deactivated': 'Switched off'}
LOGIN_CLASSES = {'invited': 'status-excused', 'active': 'status-present', 'deactivated': 'status-enrolled'}
LESSON_CLASSES = {
    'pending': 'status-excused', 'accepted': 'status-present',
    'declined': 'status-absent', 'cancelled': 'status-enrolled',
}


@register.simple_tag
def weapon_tag(weapon):
    if not weapon:
        return ''
    return format_html('<span class="tag weapon-{}">{}</span>', weapon, WEAPONS[weapon])


@register.simple_tag
def active_tag(active):
    if active:
        return format_html('<span class="tag status-present">Active</span>')
    return format_html('<span class="tag status-enrolled">Inactive</span>')


@register.simple_tag
def login_tag(status):
    return format_html('<span class="tag {}">{}</span>', LOGIN_CLASSES[status], LOGIN_LABELS[status])


@register.simple_tag
def lesson_status(status):
    label = LessonRequest.Status(status).label
    return format_html('<span class="tag {}">{}</span>', LESSON_CLASSES[status], label)


@register.filter
def headcount(fencing_class):
    """Present out of capacity, or out of the roster if there's no capacity."""
    total = fencing_class.capacity or fencing_class.member_count
    return f'{fencing_class.present_count}/{total}'


@register.inclusion_tag('web/rate_bar.html')
def rate_bar(member):
    """Present out of present + absent. Excused and not-yet-marked classes don't count."""
    if not member.marked_count:
        return {'rate': None}
    return {'rate': round(100 * member.present_count / member.marked_count)}


@register.inclusion_tag('web/status_select.html')
def status_select(row, editable, source='class'):
    """A row's attendance status: a dropdown that saves itself, or just a tag."""
    return {'row': row, 'editable': editable, 'source': source, 'statuses': ATTENDANCE}
