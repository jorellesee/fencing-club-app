"""Helpers every page uses: who's allowed in, and htmx's response headers.

htmx response headers:
- HX-Trigger fires events in the browser, e.g. `sessionsChanged` makes the calendar
  reload its events. HX-Trigger-After-Swap fires `closeModal` once a dialog has saved.
- HX-Retarget and HX-Reswap put the response somewhere other than where the
  request asked, e.g. a saved form's dialog is replaced by the class's panel.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from club.roles import COACH, MANAGER, MEMBER, role_of

EVERYONE = (MANAGER, COACH, MEMBER)


def role_required(*roles):
    """Logged in, with one of `roles`, which the view can read as `request.role`.
    htmx requests get HX-Redirect instead of a redirect, so the login page replaces
    the whole page rather than a panel."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if is_htmx(request):
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


def is_htmx(request):
    return bool(request.headers.get('HX-Request'))


def parse_range(request):
    """The start and end FullCalendar asks for, as times."""
    start = parse_datetime(request.GET.get('start', ''))
    end = parse_datetime(request.GET.get('end', ''))
    if not (start and end):
        raise Http404
    return start, end


def when(moment):
    """e.g. "Fri 6 Nov, 10:00", for messages."""
    return timezone.localtime(moment).strftime('%a %-d %b, %H:%M')
