"""Logging in and out, and choosing a password from an emailed link."""
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from club import services
from club.emails import display_name, send_password_reset, user_from_link
from club.roles import role_of

from ..forms import ChoosePasswordForm, ForgotPasswordForm, LoginForm


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if role_of(request.user):
        return redirect('calendar')
    form = LoginForm(request.POST or None)
    error = ''
    if form.is_valid():
        username = services.username_for(form.cleaned_data['username'])
        if services.too_many_attempts('login', username.lower(), limit=10):
            error = 'Too many attempts. Try again in 15 minutes.'
        else:
            user = authenticate(request, username=username, password=form.cleaned_data['password'])
            if user is None or role_of(user) is None:
                error = 'Wrong username or password.'
            else:
                login(request, user)
                if settings.POSTHOG_MW_CLIENT:
                    settings.POSTHOG_MW_CLIENT.capture('user_logged_in')
                next_url = request.GET.get('next', '')
                # Only paths on this site, so a link can't send someone elsewhere.
                safe = next_url.startswith('/') and not next_url.startswith('//')
                return redirect(next_url if safe else 'calendar')
    return render(request, 'web/auth/login.html', {'form': form, 'error': error})


@require_POST
def logout_view(request):
    if settings.POSTHOG_MW_CLIENT:
        settings.POSTHOG_MW_CLIENT.capture('user_logged_out')
    logout(request)
    return redirect('login')


@require_http_methods(['GET', 'POST'])
def forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)
    sent = False
    if form.is_valid():
        email = form.cleaned_data['email']
        if not services.too_many_attempts('reset', email.lower(), limit=3):
            for user in User.objects.filter(email__iexact=email, is_active=True):
                if role_of(user) is not None:
                    send_password_reset(user)
        # The same answer either way, so nobody can use this to find out who has a login.
        sent = True
    return render(request, 'web/auth/forgot_password.html', {'form': form, 'sent': sent})


@require_http_methods(['GET', 'POST'])
def set_password(request, uidb64, token):
    """Where invite and password reset emails link to."""
    user = user_from_link(uidb64, token)
    if user is None:
        return render(request, 'web/auth/bad_link.html', status=400)
    form = ChoosePasswordForm(user, request.POST or None)
    if form.is_valid():
        form.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        if settings.POSTHOG_MW_CLIENT:
            settings.POSTHOG_MW_CLIENT.capture('user_logged_in', properties={
                'login_method': 'password_setup',
            })
        return redirect('calendar')
    return render(request, 'web/auth/set_password.html', {
        'form': form,
        'username': user.get_username(),
        'name': display_name(user),
        'invited': not user.has_usable_password(),
    })
