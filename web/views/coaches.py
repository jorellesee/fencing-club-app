"""Coaches: the list with its side peek, and the Login row shared with members."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from club import queries, services
from club.models import Coach, Member
from club.roles import MANAGER, login_of

from ..forms import CoachForm
from .common import htmx, is_htmx, role_required


def details_context(pk):
    coach = get_object_or_404(queries.coaches(), pk=pk)
    now = timezone.now()
    own = queries.classes().filter(coach=coach)
    # Five each, so a long weekly series doesn't fill the panel.
    return {
        'coach': coach,
        'login': login_of(coach),
        'members': Member.objects.filter(primary_coach=coach).order_by('name'),
        'upcoming': own.filter(end__gte=now)[:5],
        'past': own.filter(end__lt=now).order_by('-start')[:5],
    }


@role_required(MANAGER)
def coach_list(request):
    selected = request.GET.get('coach', '')
    selected = int(selected) if selected.isdigit() else None
    context = {'coaches': queries.coaches(), 'selected': selected}
    if selected:
        context.update(details_context(selected))
    return render(request, 'web/coaches/list.html', context)


@role_required(MANAGER)
def coach_panel(request, pk):
    """The side peek. A normal visit, e.g. an old bookmark, gets the list with it open."""
    if not is_htmx(request):
        return redirect(f"{reverse('coaches')}?coach={pk}")
    return render(request, 'web/coaches/panel.html', details_context(pk))


@role_required(MANAGER)
@require_http_methods(['GET', 'POST'])
def coach_form(request, pk=None):
    instance = get_object_or_404(Coach, pk=pk) if pk else None
    form = CoachForm(request.POST or None, instance=instance)
    if form.is_valid():
        saved = form.save()
        if instance is None:
            response = render(request, 'web/coaches/panel.html', details_context(saved.pk))
            return htmx(response, trigger=['coachesChanged'], close_modal=True, retarget='#panel',
                        push_url=f"{reverse('coaches')}?coach={saved.pk}")
        response = render(request, 'web/coaches/details.html', details_context(saved.pk))
        return htmx(response, trigger=['coachesChanged'], close_modal=True,
                    retarget='#coach-details', reswap='outerHTML')
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
