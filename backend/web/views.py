"""The app's pages. Each view returns HTML: a whole page for a normal visit, or just
the piece that changed when htmx asks (the `HX-Request` header is set).

htmx response headers used here:
- HX-Trigger fires events in the browser, e.g. `classesChanged` makes the calendar
  reload its events. HX-Trigger-After-Swap fires `closeModal` once a dialog has saved.
- HX-Retarget and HX-Reswap put the response somewhere other than where the
  request asked, e.g. a saved form's dialog is replaced by the class's panel.
"""
import json
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Max, Min, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods, require_POST

from club import services
from club.emails import display_name, send_password_reset, user_from_link
from club.models import Attendance, Coach, FencingClass, LessonRequest, Member
from club.permissions import COACH, MANAGER, MEMBER, role_of
from club.serializers import login_status

from .forms import (
    ChoosePasswordForm, ClassForm, CoachForm, ForgotPasswordForm, LessonRequestForm,
    LoginForm, MemberForm, OwnDetailsForm, RepeatForm,
)

EVERYONE = (MANAGER, COACH, MEMBER)


# Helpers

def role_required(*roles):
    """Logged in, with one of `roles`. htmx requests get HX-Redirect instead of a
    redirect, so the login page replaces the whole page rather than a panel."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('HX-Request'):
                    return HttpResponse(headers={'HX-Redirect': reverse('login')})
                return redirect(f"{reverse('login')}?next={request.get_full_path()}")
            request.role = role_of(request.user)
            if request.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def htmx(response, trigger=(), retarget=None, reswap=None, push_url=None, close_modal=False):
    """Adds htmx's response headers to `response`."""
    if trigger:
        response['HX-Trigger'] = ', '.join(trigger)
    if close_modal:
        # After the swap: closing first would remove the form that made the
        # request, and htmx doesn't swap for a request whose element has gone.
        response['HX-Trigger-After-Swap'] = 'closeModal'
    if retarget:
        response['HX-Retarget'] = retarget
        response['HX-Reswap'] = reswap or 'innerHTML'
    if push_url:
        response['HX-Push-Url'] = push_url
    return response


def first_error(error):
    return services.error_text(error)


def own_coach_id(user):
    """A coach login's coach, or 0 (matching nothing) if it isn't linked to one."""
    return user.profile.coach_id or 0


def can_edit_class(request, fencing_class):
    """Managers edit anything, coaches only their own classes. Mirrors the API."""
    return request.role == MANAGER or (
        request.role == COACH and fencing_class.coach_id == request.user.profile.coach_id
        and fencing_class.coach_id is not None
    )


def classes():
    return FencingClass.objects.select_related('coach').annotate(
        member_count=Count('attendance'),
        present_count=Count('attendance', filter=Q(attendance__status='present')),
    )


def members():
    return Member.objects.annotate(
        present_count=Count('attendance', filter=Q(attendance__status='present')),
        marked_count=Count('attendance', filter=Q(attendance__status__in=['present', 'absent'])),
        last_present=Max('attendance__fencing_class__start', filter=Q(attendance__status='present')),
    ).select_related('profile__user', 'primary_coach').order_by('name')


def coaches():
    return Coach.objects.annotate(
        class_count=Count('classes'),
        next_class=Min('classes__start', filter=Q(classes__start__gte=timezone.now())),
    ).select_related('profile__user')


def mine(user):
    """The classes a member is on. A subquery, so headcounts stay whole-class."""
    return Q(id__in=Attendance.objects.filter(member__profile__user=user).values('fencing_class'))


def bookable():
    """Upcoming classes. Private lessons are never open to other members."""
    return Q(start__gt=timezone.now(), lesson_request__isnull=True)


def visible_class(request, pk):
    """A class this person may open: any for staff and coaches, and for members
    their own or ones they could book."""
    queryset = classes()
    if request.role == MEMBER:
        queryset = queryset.filter(mine(request.user) | bookable())
    return get_object_or_404(queryset, pk=pk)


FILTERS = ['coach', 'member', 'location', 'weapon']


def class_filters(request):
    """The filters in the URL, which managers set on the Classes page."""
    return {key: request.GET.get(key, '') for key in FILTERS}


def filtered_classes(request):
    """What the calendar and the list show: a manager's filtered classes, a coach's
    own, a member's own."""
    queryset = classes()
    if request.role == MANAGER:
        filters = class_filters(request)
        if filters['coach']:
            queryset = queryset.filter(coach=filters['coach'])
        if filters['member']:
            queryset = queryset.filter(mine_of(filters['member']))
        if filters['location']:
            queryset = queryset.filter(location=filters['location'])
        if filters['weapon']:
            queryset = queryset.filter(weapon=filters['weapon'])
    elif request.role == COACH:
        queryset = queryset.filter(coach=own_coach_id(request.user))
    else:
        queryset = queryset.filter(mine(request.user))
    return queryset


def mine_of(member_id):
    return Q(id__in=Attendance.objects.filter(member=member_id).values('fencing_class'))


def filter_options(request):
    return {
        'filters_json': json.dumps(class_filters(request)),
        'coach_options': Coach.objects.all(),
        'member_options': Member.objects.order_by('name'),
        'location_options': locations(),
        'weapon_options': FencingClass.Weapon.choices,
    }


def locations():
    return (
        FencingClass.objects.exclude(location='')
        .order_by('location')
        .values_list('location', flat=True)
        .distinct()
    )


def parse_range(request):
    start = parse_datetime(request.GET.get('start', ''))
    end = parse_datetime(request.GET.get('end', ''))
    if not (start and end):
        raise Http404
    return start, end


# Logging in

@require_http_methods(['GET', 'POST'])
def login_view(request):
    if role_of(request.user):
        return redirect('calendar')
    form = LoginForm(request.POST or None)
    error = ''
    if form.is_valid():
        username = services.username_for(form.cleaned_data['username'])
        if services.too_many_attempts('login', username.lower(), limit=10):
            error = 'Too many attempts. Try again in 15 minutes.'
        else:
            user = authenticate(request, username=username, password=form.cleaned_data['password'])
            if user is None or role_of(user) is None:
                error = 'Wrong username or password.'
            else:
                login(request, user)
                next_url = request.GET.get('next', '')
                return redirect(next_url if next_url.startswith('/') else 'calendar')
    return render(request, 'web/login.html', {'form': form, 'error': error})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


@require_http_methods(['GET', 'POST'])
def forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)
    sent = False
    if form.is_valid():
        email = form.cleaned_data['email']
        if not services.too_many_attempts('reset', email.lower(), limit=3):
            for user in User.objects.filter(email__iexact=email, is_active=True):
                if role_of(user) is not None:
                    send_password_reset(user)
        # The same answer either way, so nobody can use this to find out who has a login.
        sent = True
    return render(request, 'web/forgot_password.html', {'form': form, 'sent': sent})


@require_http_methods(['GET', 'POST'])
def set_password(request, uidb64, token):
    """Where invite and password reset emails link to."""
    user = user_from_link(uidb64, token)
    if user is None:
        return render(request, 'web/bad_link.html', status=400)
    form = ChoosePasswordForm(user, request.POST or None)
    if form.is_valid():
        form.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('calendar')
    return render(request, 'web/set_password.html', {
        'form': form,
        'username': user.get_username(),
        'name': display_name(user),
        'invited': not user.has_usable_password(),
    })


# Classes: the calendar and the list

@role_required(*EVERYONE)
def calendar(request):
    return render(request, 'web/calendar.html', {
        **filter_options(request),
    })


@role_required(*EVERYONE)
def calendar_events(request):
    """The classes, and pending lesson requests, FullCalendar shows for one week."""
    start, end = parse_range(request)
    events = [
        {
            'id': str(c.id),
            'title': f'{c.name} ({c.present_count}/{c.capacity or c.member_count})',
            'start': c.start.isoformat(),
            'end': c.end.isoformat(),
            'extendedProps': {'panel': reverse('class_panel', args=[c.id])},
        }
        for c in filtered_classes(request).filter(start__lt=end, end__gt=start)
    ]
    for lesson in pending_requests(request).filter(start__lt=end, end__gt=start):
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


def pending_requests(request):
    queryset = LessonRequest.objects.filter(
        status=LessonRequest.Status.PENDING
    ).select_related('member', 'coach')
    if request.role == MANAGER:
        filters = class_filters(request)
        # Requests have no location or weapon, so those filters hide them.
        if filters['location'] or filters['weapon']:
            return queryset.none()
        if filters['coach']:
            queryset = queryset.filter(coach=filters['coach'])
        if filters['member']:
            queryset = queryset.filter(member=filters['member'])
        return queryset
    if request.role == COACH:
        return queryset.filter(coach=own_coach_id(request.user))
    return queryset.filter(member__profile__user=request.user)


@role_required(*EVERYONE)
def class_table(request):
    rows = filtered_classes(request)
    now = timezone.now()
    my_status = {}
    if request.role == MEMBER:
        my_status = dict(
            Attendance.objects.filter(member__profile__user=request.user)
            .values_list('fencing_class', 'status')
        )
    rows = [*rows]
    for row in rows:
        row.my_status = my_status.get(row.id)
    return render(request, 'web/class_table.html', {
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


# Classes: the side panel

def class_panel_response(request, pk, message='', trigger=()):
    fencing_class = visible_class(request, pk)
    rows = fencing_class.attendance.select_related('member').order_by('member__name')
    if request.role == MEMBER:
        rows = rows.filter(member__profile__user=request.user)
    context = {
        'c': fencing_class,
        'rows': rows,
        'editable': can_edit_class(request, fencing_class),
        'message': message,
        'upcoming': fencing_class.start > timezone.now(),
    }
    if request.role == MANAGER:
        context['available'] = Member.objects.filter(active=True).exclude(
            attendance__fencing_class=fencing_class
        ).order_by('name')
        context['repeat_form'] = RepeatForm()
    return htmx(render(request, 'web/class_panel.html', context), trigger=trigger)


@role_required(*EVERYONE)
def class_panel(request, pk):
    return class_panel_response(request, pk)


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
        response = class_panel_response(request, saved.pk)
        return htmx(response, trigger=['classesChanged'], close_modal=True, retarget='#panel')
    return render(request, 'web/class_form.html', {
        'form': form, 'editing': instance is not None, 'locations': locations(),
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
    if not can_edit_class(request, fencing_class):
        raise PermissionDenied
    fencing_class.notes = request.POST.get('notes', '')
    fencing_class.save(update_fields=['notes'])
    return HttpResponse(status=204)


@role_required(MANAGER, COACH)
@require_POST
def set_status(request, pk):
    """The status dropdown, in a class's panel or a member's history."""
    row = get_object_or_404(Attendance.objects.select_related('fencing_class'), pk=pk)
    if not can_edit_class(request, row.fencing_class):
        raise PermissionDenied
    status = request.POST.get('status')
    if status not in Attendance.Status.values:
        return HttpResponse(status=400)
    row.status = status
    row.save(update_fields=['status'])
    if request.GET.get('from') == 'member':
        return member_details_response(request, row.member_id, trigger=['membersChanged'])
    return class_panel_response(request, row.fencing_class_id, trigger=['classesChanged'])


@role_required(MANAGER)
@require_POST
def add_to_class(request, pk):
    fencing_class = get_object_or_404(FencingClass, pk=pk)
    member = get_object_or_404(Member, pk=request.POST.get('member'))
    Attendance.objects.get_or_create(
        fencing_class=fencing_class, member=member, defaults={'status': 'enrolled'}
    )
    return class_panel_response(request, pk, trigger=['classesChanged'])


@role_required(MANAGER)
@require_POST
def remove_from_class(request, pk):
    row = get_object_or_404(Attendance, pk=pk)
    row.delete()
    return class_panel_response(request, row.fencing_class_id, trigger=['classesChanged'])


@role_required(MEMBER)
@require_POST
def enrol(request, pk):
    fencing_class = visible_class(request, pk)
    message = ''
    try:
        if request.POST.get('enrolled') == '1':
            services.enrol(services.own_member(request.user), fencing_class)
        else:
            services.unenrol(request.user, fencing_class)
    except ValidationError as error:
        message = first_error(error)
    return class_panel_response(request, pk, message=message, trigger=['classesChanged'])


@role_required(MANAGER)
@require_POST
def repeat(request, pk):
    fencing_class = get_object_or_404(FencingClass, pk=pk)
    form = RepeatForm(request.POST)
    if not form.is_valid():
        return class_panel_response(request, pk, message='Choose a date to repeat until.')
    try:
        created = services.repeat_weekly(fencing_class, form.cleaned_data['until'])
    except ValidationError as error:
        return class_panel_response(request, pk, message=first_error(error))
    return class_panel_response(
        request, pk, message=f'Added {created} more classes.', trigger=['classesChanged']
    )


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


# Lesson requests on the calendar

def visible_request(request, pk):
    queryset = LessonRequest.objects.select_related('member', 'coach')
    if request.role == COACH:
        queryset = queryset.filter(coach=own_coach_id(request.user))
    elif request.role == MEMBER:
        queryset = queryset.filter(member__profile__user=request.user)
    return get_object_or_404(queryset, pk=pk)


@role_required(*EVERYONE)
def lesson_request_panel(request, pk, error=''):
    return render(request, 'web/lesson_request_panel.html', {
        'lesson': visible_request(request, pk), 'error': error,
    })


@role_required(*EVERYONE)
@require_POST
def answer_request(request, pk, verb):
    """Accept or decline (the coach or a manager), or cancel (the member who asked)."""
    lesson = visible_request(request, pk)
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
        return lesson_request_panel(request, pk, error=first_error(error))
    if verb == 'accept':
        # Open the new class, ready to mark.
        return class_panel_response(request, lesson.fencing_class_id, trigger=['classesChanged'])
    return htmx(HttpResponse(), trigger=['classesChanged'])


# Members' own pages

@role_required(MEMBER)
def book(request, message='', error=''):
    """Upcoming classes a member isn't on yet, to enrol themselves in."""
    rows = classes().filter(bookable()).exclude(mine(request.user))
    for row in rows:
        row.spots = None if row.capacity is None else max(row.capacity - row.member_count, 0)
    template = 'web/book_list.html' if request.headers.get('HX-Request') else 'web/book.html'
    return render(request, template, {'rows': rows, 'message': message, 'error': error})


@role_required(MEMBER)
@require_POST
def book_class(request, pk):
    fencing_class = visible_class(request, pk)
    try:
        services.enrol(services.own_member(request.user), fencing_class)
    except ValidationError as error:
        return book(request, error=first_error(error))
    when = timezone.localtime(fencing_class.start).strftime('%a %-d %b, %H:%M')
    return book(request, message=f'You’re enrolled in {fencing_class.name}, {when}.')


@role_required(MEMBER)
def lessons(request, message='', error=''):
    """Pick a coach, then drag across a free time to ask for a lesson."""
    try:
        coach_options = services.coaches_of(services.own_member(request.user))
    except ValidationError as err:
        coach_options, error = Coach.objects.none(), first_error(err)
    current = LessonRequest.objects.filter(
        member__profile__user=request.user, end__gte=timezone.now()
    ).select_related('coach')
    context = {
        'coach_options': coach_options, 'current': current, 'message': message, 'error': error,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'web/my_lessons.html', context)
    return render(request, 'web/lessons.html', context)


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
        'pending': ('Requested', 'yellow'),
        'accepted': ('Your lesson', 'green'),
    }
    for lesson in LessonRequest.objects.filter(
        member=member, coach=coach, status__in=own, start__lt=end, end__gt=start
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
            error = first_error(err)
        else:
            when = timezone.localtime(lesson.start).strftime('%a %-d %b, %H:%M')
            response = lessons(
                request, message=f'Asked {coach.name} for {when}. It’s pending until they reply.'
            )
            return htmx(response, trigger=['lessonsChanged'], close_modal=True,
                        retarget='#my-lessons', reswap='outerHTML')
    return render(request, 'web/lesson_form.html', {'form': form, 'coach': coach, 'error': error})


@role_required(MEMBER)
@require_POST
def cancel_lesson(request, pk):
    lesson = visible_request(request, pk)
    try:
        services.cancel_lesson(lesson)
    except ValidationError as error:
        return lessons(request, error=first_error(error))
    when = timezone.localtime(lesson.start).strftime('%a %-d %b, %H:%M')
    return htmx(lessons(request, message=f'Cancelled your lesson on {when}.'),
                trigger=['lessonsChanged'])


@role_required(MEMBER)
def profile(request):
    member = request.user.profile.member
    if member is None:
        raise Http404
    return render(request, 'web/profile.html', member_details_context(request, member.id))


# Members

@role_required(MANAGER)
def member_list(request):
    selected = request.GET.get('member', '')
    selected = int(selected) if selected.isdigit() else None
    context = {'members': members(), 'selected': selected}
    if selected:
        context.update(member_details_context(request, selected))
    return render(request, 'web/members.html', context)


def member_details_context(request, pk):
    queryset = members()
    if request.role == MEMBER:
        queryset = queryset.filter(profile__user=request.user)
    member = get_object_or_404(queryset, pk=pk)
    history = member.attendance.select_related('fencing_class').order_by('-fencing_class__start')
    for row in history:
        row.editable = can_edit_class(request, row.fencing_class)
    return {'member': member, 'history': history, 'login': login_of(member)}


def member_details_response(request, pk, trigger=()):
    context = member_details_context(request, pk)
    return htmx(render(request, 'web/member_details.html', context), trigger=trigger)


@role_required(MANAGER)
def member_panel(request, pk):
    return render(request, 'web/member_panel.html', member_details_context(request, pk))


@role_required(MANAGER, MEMBER)
@require_http_methods(['GET', 'POST'])
def member_form(request, pk=None):
    """New member or edit member for managers. Members edit their own details."""
    if request.role == MEMBER:
        instance = get_object_or_404(Member, pk=pk, profile__user=request.user)
        form_class = OwnDetailsForm
    else:
        instance = get_object_or_404(Member, pk=pk) if pk else None
        form_class = MemberForm
    form = form_class(request.POST or None, instance=instance)
    if form.is_valid():
        saved = form.save()
        trigger = ['membersChanged']
        if instance is None:
            response = member_panel(request, saved.pk)
            return htmx(response, trigger=trigger, close_modal=True, retarget='#panel',
                        push_url=f"{reverse('members')}?member={saved.pk}")
        return htmx(member_details_response(request, saved.pk), trigger=trigger,
                    close_modal=True, retarget='#member-details', reswap='outerHTML')
    return render(request, 'web/member_form.html', {'form': form, 'editing': instance is not None})


# Coaches

@role_required(MANAGER)
def coach_list(request):
    return render(request, 'web/coaches.html', {'coaches': coaches()})


@role_required(MANAGER)
def coach_page(request, pk):
    coach = get_object_or_404(coaches(), pk=pk)
    now = timezone.now()
    own = classes().filter(coach=coach)
    # Ten each, so a long weekly series doesn't fill the page.
    return render(request, 'web/coach.html', {
        'coach': coach,
        'login': login_of(coach),
        'members': Member.objects.filter(primary_coach=coach).order_by('name'),
        'upcoming': own.filter(end__gte=now)[:10],
        'past': own.filter(end__lt=now).order_by('-start')[:10],
    })


@role_required(MANAGER)
@require_http_methods(['GET', 'POST'])
def coach_form(request, pk=None):
    instance = get_object_or_404(Coach, pk=pk) if pk else None
    form = CoachForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        # A whole new page is simplest here: the list, or the coach's page.
        return HttpResponse(headers={'HX-Refresh': 'true'})
    return render(request, 'web/coach_form.html', {'form': form, 'editing': instance is not None})


# Logins: the Login row on a member's or coach's details

def login_of(person):
    """A member's or coach's login user and its status, or None if never invited."""
    profile = getattr(person, 'profile', None)
    if profile is None:
        return None
    return {'id': profile.user_id, 'status': login_status(profile.user)}


def login_row(request, person, kind, notice='', error=''):
    return render(request, 'web/login_row.html', {
        'person': person, 'kind': kind, 'login': login_of(person),
        'notice': notice, 'error': error,
    })


@role_required(MANAGER)
@require_POST
def invite(request, kind, pk):
    """Invite to log in, or resend the invite."""
    person = get_object_or_404(Member if kind == 'member' else Coach, pk=pk)
    try:
        services.invite(**{kind: person})
    except ValidationError as error:
        return login_row(request, person, kind, error=first_error(error))
    return login_row(request, person, kind, notice=f'Sent to {person.email}')


@role_required(MANAGER)
@require_POST
def set_login_active(request, pk):
    """Switch a login off, or back on."""
    user = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    profile = user.profile
    person, kind = (profile.member, 'member') if profile.member else (profile.coach, 'coach')
    user.is_active = request.POST.get('active') == '1'
    user.save(update_fields=['is_active'])
    notice = 'They can log in again' if user.is_active else 'They can no longer log in'
    return login_row(request, person, kind, notice=notice)
