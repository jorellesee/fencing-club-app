from rest_framework.permissions import SAFE_METHODS, BasePermission

MANAGER = 'manager'
COACH = 'coach'
MEMBER = 'member'


def role_of(user):
    """'manager' for staff, the profile's role for everyone else, or None."""
    if not user.is_authenticated:
        return None
    if user.is_staff:
        return MANAGER
    profile = getattr(user, 'profile', None)
    return profile.role if profile else None


class RoleAccess(BasePermission):
    """Managers can do anything. Coaches and members can only use the actions a
    viewset lists for them in `role_actions`, only change the fields listed in
    `role_fields`, and only change objects the viewset's `can_edit` allows."""

    def has_permission(self, request, view):
        role = role_of(request.user)
        if role == MANAGER:
            return True
        if view.action not in getattr(view, 'role_actions', {}).get(role, ()):
            return False
        if request.method in SAFE_METHODS:
            return True
        return set(request.data) <= getattr(view, 'role_fields', {}).get(role, set())

    def has_object_permission(self, request, view, obj):
        if role_of(request.user) == MANAGER or request.method in SAFE_METHODS:
            return True
        return view.can_edit(request.user, obj)
