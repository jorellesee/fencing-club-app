"""Book a session: upcoming group sessions a member isn’t on yet, to enrol in."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from club import queries, services
from club.roles import MEMBER

from ..posthog_logs import logger as posthog_logger
from .common import is_htmx, role_required, when


@role_required(MEMBER)
def book(request, message='', error=''):
    rows = queries.bookable_sessions(request.user)
    for row in rows:
        row.spots = None if row.capacity is None else max(row.capacity - row.member_count, 0)
    template = 'web/book/list.html' if is_htmx(request) else 'web/book/page.html'
    return render(request, template, {'rows': rows, 'message': message, 'error': error})


@role_required(MEMBER)
@require_POST
def book_session(request, pk):
    session = get_object_or_404(queries.visible_sessions(request.user), pk=pk)
    try:
        services.enrol(services.own_member(request.user), session)
    except ValidationError as error:
        return book(request, error=services.error_text(error))
    if settings.POSTHOG_MW_CLIENT:
        settings.POSTHOG_MW_CLIENT.capture('session_booking_completed', properties={
            'session_id': session.pk,
            'session_category': session.category,
            'session_weapon': session.weapon,
        })
    posthog_logger.info('session booking completed', extra={
        'event': 'session_booking_completed',
        'session_id': session.pk,
        'session_category': session.category,
    })
    message = f'You’re enrolled in {session.name}, {when(session.start)}.'
    return book(request, message=message)
