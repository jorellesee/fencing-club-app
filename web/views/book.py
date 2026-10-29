"""Book a class: upcoming classes a member isn't on yet, to enrol themselves in."""
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from club import queries, services
from club.roles import MEMBER

from .common import is_htmx, role_required, when


@role_required(MEMBER)
def book(request, message='', error=''):
    rows = queries.bookable_classes(request.user)
    for row in rows:
        row.spots = None if row.capacity is None else max(row.capacity - row.member_count, 0)
    template = 'web/book/list.html' if is_htmx(request) else 'web/book/page.html'
    return render(request, template, {'rows': rows, 'message': message, 'error': error})


@role_required(MEMBER)
@require_POST
def book_class(request, pk):
    fencing_class = get_object_or_404(queries.visible_classes(request.user), pk=pk)
    try:
        services.enrol(services.own_member(request.user), fencing_class)
    except ValidationError as error:
        return book(request, error=services.error_text(error))
    message = f'You’re enrolled in {fencing_class.name}, {when(fencing_class.start)}.'
    return book(request, message=message)
