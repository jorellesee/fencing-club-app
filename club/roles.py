"""Who someone is to the club: a manager (any staff user), a coach or a member."""

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


def login_status(user):
    """'invited' until the password is set, then 'active' or 'deactivated'."""
    if not user.is_active:
        return 'deactivated'
    return 'active' if user.has_usable_password() else 'invited'


def login_of(person):
    """A member's or coach's login and its status, or None if they haven't been invited."""
    profile = getattr(person, 'profile', None)
    if profile is None:
        return None
    return {'id': profile.user_id, 'status': login_status(profile.user)}
