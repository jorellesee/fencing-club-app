from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def identify_posthog_user(sender, request, user, **kwargs):
    """Identify the ambient PostHog request context after Django logs a user in."""
    posthog_client = settings.POSTHOG_MW_CLIENT
    if posthog_client is None:
        return

    distinct_id = str(user.pk)
    posthog_client.identify_context(distinct_id)
    posthog_client.set(
        distinct_id=distinct_id,
        properties={
            'email': user.email,
            'username': user.get_username(),
            'is_staff': user.is_staff,
        },
    )


class WebConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'web'
