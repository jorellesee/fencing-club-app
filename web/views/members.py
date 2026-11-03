"""Members: the manager's Members page with its side peek, and a member's My profile."""
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from club import queries
from club.models import Member
from club.roles import MANAGER, MEMBER, login_of

from ..forms import MemberForm, OwnDetailsForm
from .common import htmx, is_htmx, role_required


def details_context(request, pk):
    member = get_object_or_404(queries.visible_members(request.user), pk=pk)
    history = queries.history(member)
    for row in history:
        row.editable = queries.can_edit_session(request.user, row.session)
    return {'member': member, 'history': history, 'login': login_of(member)}


def details(request, pk, trigger=()):
    """A member's details, shared by the peek and My profile."""
    response = render(request, 'web/members/details.html', details_context(request, pk))
    return htmx(response, trigger=trigger)


@role_required(MANAGER)
def member_list(request):
    selected = request.GET.get('member', '')
    selected = int(selected) if selected.isdigit() else None
    context = {'members': queries.members(), 'selected': selected}
    if selected:
        context.update(details_context(request, selected))
    return render(request, 'web/members/list.html', context)


@role_required(MANAGER)
def member_panel(request, pk):
    """The side peek. A normal visit, e.g. an old bookmark, gets the list with it open."""
    if not is_htmx(request):
        return redirect(f"{reverse('members')}?member={pk}")
    return render(request, 'web/members/panel.html', details_context(request, pk))


@role_required(MEMBER)
def profile(request):
    member = request.user.profile.member
    if member is None:
        raise Http404
    return render(request, 'web/members/profile.html', details_context(request, member.id))


@role_required(MANAGER, MEMBER)
@require_http_methods(['GET', 'POST'])
def member_form(request, pk=None):
    """New member or edit member for managers. Members edit their own details."""
    if request.role == MEMBER:
        if pk is None:
            raise PermissionDenied
        instance = get_object_or_404(Member, pk=pk, profile__user=request.user)
        form_class = OwnDetailsForm
    else:
        instance = get_object_or_404(Member, pk=pk) if pk else None
        form_class = MemberForm
    form = form_class(request.POST or None, instance=instance)
    if form.is_valid():
        saved = form.save()
        if instance is None:
            return htmx(member_panel(request, saved.pk), trigger=['membersChanged'],
                        close_modal=True, retarget='#panel',
                        push_url=f"{reverse('members')}?member={saved.pk}")
        return htmx(details(request, saved.pk), trigger=['membersChanged'], close_modal=True,
                    retarget='#member-details', reswap='outerHTML')
    return render(request, 'web/members/form.html', {
        'form': form, 'editing': instance is not None,
    })
