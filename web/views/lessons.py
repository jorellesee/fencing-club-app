"""Private lessons: the member's Private lessons page, and the request panel that
opens from the calendar for the coach, a manager, or the member who asked.

A lesson is an individual TrainingSession. A request is one that's unconfirmed."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods, require_POST

from club import queries, services
from club.models import Coach
from club.roles import MEMBER

from ..forms import LessonRequestForm
from .sessions import panel
from .common import EVERYONE, htmx, is_htmx, parse_range, role_required, when


# The request panel, on the calendar

@role_required(*EVERYONE)
def request_panel(request, pk, error=''):
    return render(request, 'web/lessons/request_panel.html', {
        'lesson': get_object_or_404(queries.shown_requests(request.user, {}), pk=pk),
        'error': error,
    })


@role_required(*EVERYONE)
@require_POST
def answer(request, pk, verb):
    """Accept or decline (the coach or a manager), or cancel (the member who asked)."""
    lesson = get_object_or_404(queries.shown_requests(request.user, {}), pk=pk)
    allowed = {'cancel'} if request.role == MEMBER else {'accept', 'decline'}
    if verb not in allowed:
        raise PermissionDenied
    try:
        {
            'accept': services.accept_lesson,
            'decline': services.decline_lesson,
            'cancel': services.cancel_lesson,
        }[verb](lesson)
    except ValidationError as error:
        return request_panel(request, pk, error=services.error_text(error))
    if verb == 'accept':
        # Open it as a session now, ready to mark.
        return panel(request, lesson.pk, trigger=['sessionsChanged'])
    return htmx(HttpResponse(), trigger=['sessionsChanged'])


# The member's Private lessons page

@role_required(MEMBER)
def lessons(request, message='', error=''):
    """Pick a coach, then drag across a free time to ask for a lesson. htmx gets
    just the My requests part."""
    try:
        coach_options = services.coaches_of(services.own_member(request.user))
    except ValidationError as err:
        coach_options, error = Coach.objects.none(), services.error_text(err)
    current = queries.visible_lessons(request.user).filter(end__gte=timezone.now())
    context = {
        'coach_options': coach_options, 'current': current, 'message': message, 'error': error,
    }
    template = 'web/lessons/mine.html' if is_htmx(request) else 'web/lessons/page.html'
    return render(request, template, context)


@role_required(MEMBER)
def lesson_events(request):
    """The chosen coach's week: busy times, and the member's own requests in full."""
    start, end = parse_range(request)
    member = services.own_member(request.user)
    coach = get_object_or_404(services.coaches_of(member), pk=request.GET.get('coach'))
    events = [
        {
            'title': 'Busy', 'start': slot['start'].isoformat(), 'end': slot['end'].isoformat(),
            'color': 'var(--tag-gray-bg)', 'contrastColor': 'var(--tag-gray-text)',
        }
        for slot in services.busy_slots(member, coach, start, end)
    ]
    own = {
        'unconfirmed': ('Requested', 'yellow'),
        'confirmed': ('Your lesson', 'green'),
    }
    for lesson in queries.visible_lessons(request.user).filter(
        coach=coach, start__lt=end, end__gt=start
    ):
        title, colour = own[lesson.status]
        events.append({
            'title': title, 'start': lesson.start.isoformat(), 'end': lesson.end.isoformat(),
            'color': f'var(--tag-{colour}-bg)', 'contrastColor': f'var(--tag-{colour}-text)',
        })
    return JsonResponse(events, safe=False)


@role_required(MEMBER)
@require_http_methods(['GET', 'POST'])
def request_lesson(request):
    member = services.own_member(request.user)
    coach = get_object_or_404(services.coaches_of(member), pk=request.GET.get('coach'))
    form = LessonRequestForm(
        request.POST or None,
        start=parse_datetime(request.GET.get('start', '')),
        end=parse_datetime(request.GET.get('end', '')),
    )
    error = ''
    if form.is_valid():
        data = form.cleaned_data
        try:
            lesson = services.request_lesson(
                request.user, coach, data['start'], data['end'], data['note']
            )
        except ValidationError as err:
            error = services.error_text(err)
        else:
            message = f'Asked {coach.name} for {when(lesson.start)}. It’s unconfirmed until they reply.'
            return htmx(lessons(request, message=message), trigger=['lessonsChanged'],
                        close_modal=True, retarget='#my-lessons', reswap='outerHTML')
    return render(request, 'web/lessons/form.html', {
        'form': form, 'coach': coach, 'error': error,
    })


@role_required(MEMBER)
@require_POST
def cancel_lesson(request, pk):
    lesson = get_object_or_404(queries.visible_lessons(request.user), pk=pk)
    try:
        services.cancel_lesson(lesson)
    except ValidationError as error:
        return lessons(request, error=services.error_text(error))
    return htmx(lessons(request, message=f'Cancelled your lesson on {when(lesson.start)}.'),
                trigger=['lessonsChanged'])
