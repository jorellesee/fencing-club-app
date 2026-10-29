"""The Classes page: the calendar, the list, and a class's side panel."""
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods, require_POST

from club import queries, services
from club.models import Attendance, Coach, FencingClass, Member
from club.roles import COACH, MANAGER, MEMBER

from ..forms import ClassForm, RepeatForm
from .common import EVERYONE, htmx, parse_range, role_required
from .members import details


def class_filters(request):
    """The filters in the URL, which managers set on the Classes page."""
    return {key: request.GET.get(key, '') for key in queries.FILTERS}


def filter_options(request):
    return {
        'filters_json': json.dumps(class_filters(request)),
        'coach_options': Coach.objects.all(),
        'member_options': Member.objects.order_by('name'),
        'location_options': queries.locations(),
        'weapon_options': FencingClass.Weapon.choices,
    }


# The calendar and the list

@role_required(*EVERYONE)
def calendar(request):
    return render(request, 'web/classes/calendar.html', filter_options(request))


@role_required(*EVERYONE)
def calendar_events(request):
    """The classes, and pending lesson requests, FullCalendar shows for one week."""
    start, end = parse_range(request)
    filters = class_filters(request)
    events = [
        {
            'id': str(c.id),
            'title': f'{c.name} ({c.present_count}/{c.capacity or c.member_count})',
            'start': c.start.isoformat(),
            'end': c.end.isoformat(),
            'extendedProps': {'panel': reverse('class_panel', args=[c.id])},
        }
        for c in queries.shown_classes(request.user, filters).filter(start__lt=end, end__gt=start)
    ]
    requests = queries.shown_requests(request.user, filters).filter(start__lt=end, end__gt=start)
    for lesson in requests:
        events.append({
            'id': f'request-{lesson.id}',
            'title': (
                f'Requested: lesson with {lesson.coach.name}' if request.role == MEMBER
                else f'Lesson request: {lesson.member.name}'
            ),
            'start': lesson.start.isoformat(),
            'end': lesson.end.isoformat(),
            # Dashed and yellow until a coach answers.
            'editable': False,
            'className': 'event-request',
            'color': 'var(--tag-yellow-bg)',
            'contrastColor': 'var(--tag-yellow-text)',
            'extendedProps': {'panel': reverse('lesson_request_panel', args=[lesson.id])},
        })
    return JsonResponse(events, safe=False)


@role_required(*EVERYONE)
def class_list(request):
    rows = [*queries.shown_classes(request.user, class_filters(request))]
    if request.role == MEMBER:
        my_status = dict(
            Attendance.objects.filter(member__profile__user=request.user)
            .values_list('fencing_class', 'status')
        )
        for row in rows:
            row.my_status = my_status.get(row.id)
    now = timezone.now()
    return render(request, 'web/classes/list.html', {
        'upcoming': [c for c in rows if c.end >= now],
        'past': [c for c in rows if c.end < now][::-1],
        **filter_options(request),
    })


@role_required(MANAGER)
@require_POST
def move_class(request, pk):
    """Dragging a class on the calendar saves its new times."""
    fencing_class = get_object_or_404(FencingClass, pk=pk)
    start = parse_datetime(request.POST.get('start', ''))
    end = parse_datetime(request.POST.get('end', ''))
    if not (start and end) or end <= start:
        return HttpResponse('End must be after start.', status=400)
    fencing_class.start, fencing_class.end = start, end
    fencing_class.save(update_fields=['start', 'end'])
    return HttpResponse(status=204)


# The side panel

def panel(request, pk, message='', trigger=()):
    """A class's panel. Most actions in it answer with the panel again."""
    fencing_class = get_object_or_404(queries.visible_classes(request.user), pk=pk)
    rows = fencing_class.attendance.select_related('member').order_by('member__name')
    if request.role == MEMBER:
        rows = rows.filter(member__profile__user=request.user)
    context = {
        'c': fencing_class,
        'rows': rows,
        'editable': queries.can_edit_class(request.user, fencing_class),
        'message': message,
        'upcoming': fencing_class.start > timezone.now(),
    }
    if request.role == MANAGER:
        context['available'] = Member.objects.filter(active=True).exclude(
            attendance__fencing_class=fencing_class
        ).order_by('name')
        context['repeat_form'] = RepeatForm()
    return htmx(render(request, 'web/classes/panel.html', context), trigger=trigger)


@role_required(*EVERYONE)
def class_panel(request, pk):
    return panel(request, pk)


@role_required(MANAGER)
@require_http_methods(['GET', 'POST'])
def class_form(request, pk=None):
    """New class, or edit class `pk`, in a dialog."""
    instance = get_object_or_404(FencingClass, pk=pk) if pk else None
    start = parse_datetime(request.GET.get('start', ''))
    end = parse_datetime(request.GET.get('end', ''))
    form = ClassForm(request.POST or None, instance=instance, start=start, end=end)
    if form.is_valid():
        saved = form.save()
        if form.cleaned_data.get('apply_to_following'):
            services.following(saved).update(
                **{field: form.cleaned_data[field] for field in services.SERIES_FIELDS}
            )
        return htmx(panel(request, saved.pk), trigger=['classesChanged'], close_modal=True,
                    retarget='#panel')
    return render(request, 'web/classes/form.html', {
        'form': form, 'editing': instance is not None, 'locations': queries.locations(),
    })


@role_required(MANAGER)
def generate_name(request):
    """The Generate button: e.g. "Monday Sabre BT Class", from what's filled in so far."""
    form = ClassForm(request.GET)
    form.is_valid()
    data = form.cleaned_data
    weapon = dict(FencingClass.Weapon.choices).get(data.get('weapon'))
    location = (data.get('location') or '').split()
    # "Bukit Timah" becomes "BT". A one-word location is kept whole: "Clementi".
    code = location[0] if len(location) == 1 else ''.join(word[0].upper() for word in location)
    weekday = data['date'].strftime('%A') if data.get('date') else ''
    name = ' '.join(part for part in [weekday, weapon, code, 'Class'] if part)
    return HttpResponse(ClassForm(initial={'name': name})['name'].as_widget())


@role_required(MANAGER, COACH)
@require_POST
def save_notes(request, pk):
    fencing_class = get_object_or_404(FencingClass, pk=pk)
    if not queries.can_edit_class(request.user, fencing_class):
        raise PermissionDenied
    fencing_class.notes = request.POST.get('notes', '')
    fencing_class.save(update_fields=['notes'])
    return HttpResponse(status=204)


@role_required(MANAGER, COACH)
@require_POST
def set_status(request, pk):
    """The status dropdown, in a class's panel or a member's history."""
    row = get_object_or_404(Attendance.objects.select_related('fencing_class'), pk=pk)
    if not queries.can_edit_class(request.user, row.fencing_class):
        raise PermissionDenied
    status = request.POST.get('status')
    if status not in Attendance.Status.values:
        return HttpResponse(status=400)
    row.status = status
    row.save(update_fields=['status'])
    if request.GET.get('from') == 'member':
        return details(request, row.member_id, trigger=['membersChanged'])
    return panel(request, row.fencing_class_id, trigger=['classesChanged'])


@role_required(MANAGER)
@require_POST
def add_to_class(request, pk):
    fencing_class = get_object_or_404(FencingClass, pk=pk)
    member = get_object_or_404(Member, pk=request.POST.get('member'))
    Attendance.objects.get_or_create(
        fencing_class=fencing_class, member=member, defaults={'status': 'enrolled'}
    )
    return panel(request, pk, trigger=['classesChanged'])


@role_required(MANAGER)
@require_POST
def remove_from_class(request, pk):
    row = get_object_or_404(Attendance, pk=pk)
    row.delete()
    return panel(request, row.fencing_class_id, trigger=['classesChanged'])


@role_required(MEMBER)
@require_POST
def enrol(request, pk):
    """Enrol, or with enrolled=0 cancel the enrolment, from the class's panel."""
    fencing_class = get_object_or_404(queries.visible_classes(request.user), pk=pk)
    message = ''
    try:
        if request.POST.get('enrolled') == '1':
            services.enrol(services.own_member(request.user), fencing_class)
        else:
            services.unenrol(request.user, fencing_class)
    except ValidationError as error:
        message = services.error_text(error)
    return panel(request, pk, message=message, trigger=['classesChanged'])


@role_required(MANAGER)
@require_POST
def repeat(request, pk):
    fencing_class = get_object_or_404(FencingClass, pk=pk)
    form = RepeatForm(request.POST)
    if not form.is_valid():
        return panel(request, pk, message='Choose a date to repeat until.')
    try:
        created = services.repeat_weekly(fencing_class, form.cleaned_data['until'])
    except ValidationError as error:
        return panel(request, pk, message=services.error_text(error))
    return panel(request, pk, message=f'Added {created} more classes.', trigger=['classesChanged'])


@role_required(MANAGER)
@require_POST
def delete_class(request, pk):
    """Deletes the class, or with following=1, it and the later ones in its series.
    The empty response clears the panel."""
    fencing_class = get_object_or_404(FencingClass, pk=pk)
    if request.POST.get('following'):
        services.following(fencing_class).delete()
    else:
        fencing_class.delete()
    return htmx(HttpResponse(), trigger=['classesChanged'])
