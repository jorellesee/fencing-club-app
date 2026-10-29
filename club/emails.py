from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode


def set_password_link(user):
    """A link to the set-password page. Django's token stops working once the
    password changes, so each link works once, and also expires after PASSWORD_RESET_TIMEOUT."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f'{settings.SITE_URL}/set-password/{uid}/{token}/'


def user_from_link(uidb64, token):
    """The user an invite or reset link is for, or None if it's expired or used."""
    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
        return None
    if user.is_active and default_token_generator.check_token(user, token):
        return user
    return None


def display_name(user):
    profile = getattr(user, 'profile', None)
    if profile and profile.member:
        return profile.member.name
    if profile and profile.coach:
        return profile.coach.name
    return user.get_username()


def send_invite(user):
    days = settings.PASSWORD_RESET_TIMEOUT // (60 * 60 * 24)
    send_mail(
        'You’re invited to the Fencing Club app',
        f'Hi {display_name(user)},\n\n'
        f'You’ve been given a login for the Fencing Club app. '
        f'Choose a password here to get started:\n\n'
        f'{set_password_link(user)}\n\n'
        f'Your username is {user.get_username()}. The link works for {days} days.\n',
        None,
        [user.email],
    )


def send_password_reset(user):
    send_mail(
        'Reset your Fencing Club password',
        f'Hi {display_name(user)},\n\n'
        f'Someone asked to reset your Fencing Club password. Choose a new one here:\n\n'
        f'{set_password_link(user)}\n\n'
        f'If it wasn’t you, you can ignore this email.\n',
        None,
        [user.email],
    )
