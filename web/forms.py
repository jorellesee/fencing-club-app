from datetime import datetime, timedelta

from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.db.models import Q
from django.utils import timezone

from club.models import Coach, Member, TrainingSession
from club.services import lesson_time_errors


def aware(date, time):
    """A date and a time typed into a form, in the club's time zone."""
    return timezone.make_aware(datetime.combine(date, time))


def coach_choices(current=None):
    """Active coaches, plus `current` so editing doesn't drop an inactive one."""
    return Coach.objects.filter(Q(active=True) | Q(id=getattr(current, 'id', None)))


class DateInput(forms.DateInput):
    input_type = 'date'


class TimeInput(forms.TimeInput):
    input_type = 'time'

    def __init__(self):
        super().__init__(format='%H:%M')


class TimesMixin:
    """`date`, `start_time` and `end_time` fields, saved as one start and end."""

    def clean(self):
        data = super().clean()
        if {'date', 'start_time', 'end_time'} <= set(data):
            data['start'] = aware(data['date'], data['start_time'])
            data['end'] = aware(data['date'], data['end_time'])
            if data['end'] <= data['start']:
                self.add_error('end_time', 'End must be after start.')
        return data


class SessionForm(TimesMixin, forms.ModelForm):
    date = forms.DateField(widget=DateInput)
    start_time = forms.TimeField(label='Start', widget=TimeInput)
    end_time = forms.TimeField(label='End', widget=TimeInput)
    weapon = forms.ChoiceField(
        choices=[('', 'None'), *TrainingSession.Weapon.choices], required=False
    )
    apply_to_following = forms.BooleanField(
        required=False,
        label='Also change the name, category, weapon, location, coach and capacity '
              'of all following sessions in this weekly series',
    )

    class Meta:
        model = TrainingSession
        fields = ['name', 'category', 'weapon', 'location', 'coach', 'capacity', 'notes']
        widgets = {
            'location': forms.TextInput(attrs={'list': 'location-options'}),
            'capacity': forms.NumberInput(attrs={'min': 1}),
        }
        help_texts = {'capacity': 'Blank for no limit. 1 makes it a private lesson.'}

    def __init__(self, *args, start=None, end=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            start, end = self.instance.start, self.instance.end
        elif not (start and end):
            # Suggest an hour-long session starting at the next full hour.
            start = timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            end = start + timedelta(hours=1)
        start, end = timezone.localtime(start), timezone.localtime(end)
        self.initial.update(date=start.date(), start_time=start.time(), end_time=end.time())
        self.fields['name'].widget.attrs['autofocus'] = True
        self.fields['coach'].queryset = coach_choices(self.instance.coach)
        self.fields['coach'].empty_label = 'None'
        if not self.instance.series:
            del self.fields['apply_to_following']

    def save(self, commit=True):
        self.instance.start = self.cleaned_data['start']
        self.instance.end = self.cleaned_data['end']
        return super().save(commit)


class RepeatForm(forms.Form):
    until = forms.DateField(widget=DateInput)


class MemberForm(forms.ModelForm):
    """Everything about a member, for managers."""

    weapon = forms.ChoiceField(choices=[('', 'None'), *Member.Weapon.choices], required=False)

    class Meta:
        model = Member
        fields = ['name', 'email', 'phone', 'weapon', 'primary_coach', 'active']
        widgets = {'phone': forms.TextInput(attrs={'type': 'tel'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autofocus'] = True
        if 'primary_coach' in self.fields:
            self.fields['primary_coach'].queryset = coach_choices(self.instance.primary_coach)
            self.fields['primary_coach'].empty_label = 'None'


class OwnDetailsForm(MemberForm):
    """What a member may change about themselves: not email, since it's also their
    login, nor what the club decides. A disabled field ignores what's posted."""

    email = forms.EmailField(
        disabled=True, required=False,
        help_text='It’s also your login, so ask a manager to change it.',
    )

    class Meta(MemberForm.Meta):
        fields = ['name', 'email', 'phone', 'weapon']


class CoachForm(forms.ModelForm):
    weapon = forms.ChoiceField(choices=[('', 'None'), *Member.Weapon.choices], required=False)

    class Meta:
        model = Coach
        fields = ['name', 'email', 'phone', 'weapon', 'active']
        widgets = {'phone': forms.TextInput(attrs={'type': 'tel'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autofocus'] = True


class LessonRequestForm(TimesMixin, forms.Form):
    date = forms.DateField(widget=DateInput)
    start_time = forms.TimeField(label='Start', widget=TimeInput)
    end_time = forms.TimeField(label='End', widget=TimeInput)
    note = forms.CharField(
        label='Note for the coach', required=False,
        widget=forms.Textarea(attrs={'placeholder': 'e.g. Want to work on my parry riposte'}),
    )

    def __init__(self, *args, start=None, end=None, **kwargs):
        super().__init__(*args, **kwargs)
        if start and end:
            start, end = timezone.localtime(start), timezone.localtime(end)
            self.initial.update(date=start.date(), start_time=start.time(), end_time=end.time())

    def clean(self):
        data = super().clean()
        if 'start' in data and not self.errors:
            for field, message in lesson_time_errors(data['start'], data['end']).items():
                self.add_error('start_time' if field == 'start' else 'end_time', message)
        return data


class LoginForm(forms.Form):
    username = forms.CharField(
        label='Email or username',
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'autofocus': True}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
    )


class ChoosePasswordForm(SetPasswordForm):
    """Django's own, which checks AUTH_PASSWORD_VALIDATORS, with shorter labels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'New password'
        self.fields['new_password1'].help_text = ''
        self.fields['new_password1'].widget.attrs['autofocus'] = True
        self.fields['new_password2'].label = 'New password again'
