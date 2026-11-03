"""Calendar sync: a secret .ics link to someone's sessions, which Google Calendar
(or any calendar app) subscribes to with "From URL"."""
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from club import ical, queries
from club.models import CalendarFeed
from club.roles import MANAGER, role_of

from .common import EVERYONE, role_required


def sync_context(request):
    feed, _ = CalendarFeed.objects.get_or_create(user=request.user)
    url = request.build_absolute_uri(reverse('calendar_feed', args=[feed.token]))
    return {'feed_url': url}


@role_required(*EVERYONE)
def calendar_sync(request):
    return render(request, 'web/feeds/page.html', sync_context(request))


@role_required(*EVERYONE)
@require_POST
def reset_feed(request):
    """A new token, so the old link stops working, e.g. if it was shared by mistake."""
    feed, _ = CalendarFeed.objects.get_or_create(user=request.user)
    feed.reset()
    context = {**sync_context(request), 'notice': 'Done. The old link no longer works.'}
    return render(request, 'web/feeds/link.html', context)


def calendar_feed(request, token):
    """The .ics file itself. No login: calendar apps fetch it on their own, so the
    token in the URL is the only check."""
    feed = get_object_or_404(CalendarFeed.objects.select_related('user'), token=token)
    user = feed.user
    role = role_of(user)
    # A switched-off login, or one without a role, gets nothing.
    if not user.is_active or role is None:
        raise Http404
    name = 'Fencing Club' if role == MANAGER else 'Fencing Club: my sessions'
    host = settings.SITE_HOST or request.get_host()
    body = ical.calendar(name, queries.feed_sessions(user), host)
    response = HttpResponse(body, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'inline; filename="fencing-club.ics"'
    return response
