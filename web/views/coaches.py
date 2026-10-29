"""Coaches: the list, each coach's page, and the Login row shared with members."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from club import queries, services
from club.models import Coach, Member
from club.roles import MANAGER, login_of

from ..forms import CoachForm
from .common import role_required


@role_required(MANAGER)
def coach_list(request):
    return render(request, 'web/coaches/list.html', {'coaches': queries.coaches()})


@role_required(MANAGER)
def coach_page(request, pk):
    coach = get_object_or_404(queries.coaches(), pk=pk)
    now = timezone.now()
    own = queries.classes().filter(coach=coach)
    # Ten each, so a long weekly series doesn't fill the page.
    return render(request, 'web/coaches/detail.html', {
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
    return render(request, 'web/coaches/form.html', {
        'form': form, 'editing': instance is not None,
    })


# Logins: the Login row on a member's or coach's details

def login_row(request, person, kind, notice='', error=''):
    return render(request, 'web/partials/login_row.html', {
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
        return login_row(request, person, kind, error=services.error_text(error))
    return login_row(request, person, kind, notice=f'Sent to {person.email}')


@role_required(MANAGER)
@require_POST
def set_login_active(request, pk):
    """Switch a coach's or member's login off, or back on."""
    user = get_object_or_404(User.objects.filter(profile__isnull=False), pk=pk)
    profile = user.profile
    person, kind = (profile.member, 'member') if profile.member else (profile.coach, 'coach')
    user.is_active = request.POST.get('active') == '1'
    user.save(update_fields=['is_active'])
    notice = 'They can log in again' if user.is_active else 'They can no longer log in'
    return login_row(request, person, kind, notice=notice)
