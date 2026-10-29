import django.db.models.deletion
from django.db import migrations, models


def names_to_coaches(apps, schema_editor):
    """Make a Coach for every coach name typed on a class or a coach login, and
    point the classes and logins at it."""
    Coach = apps.get_model('club', 'Coach')
    FencingClass = apps.get_model('club', 'FencingClass')
    Profile = apps.get_model('club', 'Profile')

    def coach_called(name):
        coach, _ = Coach.objects.get_or_create(name=name.strip())
        return coach

    for fencing_class in FencingClass.objects.exclude(coach_name=''):
        fencing_class.coach = coach_called(fencing_class.coach_name)
        fencing_class.save(update_fields=['coach'])
    for profile in Profile.objects.filter(role='coach').exclude(old_coach_name=''):
        coach = coach_called(profile.old_coach_name)
        if not coach.email:
            coach.email = profile.user.email
            coach.save(update_fields=['email'])
        profile.coach = coach
        profile.save(update_fields=['coach'])


def coaches_to_names(apps, schema_editor):
    FencingClass = apps.get_model('club', 'FencingClass')
    Profile = apps.get_model('club', 'Profile')
    for fencing_class in FencingClass.objects.exclude(coach=None).select_related('coach'):
        fencing_class.coach_name = fencing_class.coach.name
        fencing_class.save(update_fields=['coach_name'])
    for profile in Profile.objects.exclude(coach=None).select_related('coach'):
        profile.old_coach_name = profile.coach.name
        profile.save(update_fields=['old_coach_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('club', '0007_fencingclass_weapon'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coach',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('phone', models.CharField(blank=True, max_length=30)),
                ('weapon', models.CharField(blank=True, choices=[('foil', 'Foil'), ('epee', 'Épée'), ('sabre', 'Sabre')], max_length=10)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name_plural': 'coaches',
                'ordering': ['name'],
            },
        ),
        # The old text fields get out of the way, so the new links can take their names.
        migrations.RenameField('fencingclass', 'coach', 'coach_name'),
        migrations.RenameField('profile', 'coach_name', 'old_coach_name'),
        migrations.AddField(
            model_name='fencingclass',
            name='coach',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='classes', to='club.coach'),
        ),
        migrations.AddField(
            model_name='profile',
            name='coach',
            field=models.OneToOneField(blank=True, help_text='Coaches only: whose classes this login can mark.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='profile', to='club.coach'),
        ),
        migrations.RunPython(names_to_coaches, coaches_to_names),
        migrations.RemoveField('fencingclass', 'coach_name'),
        migrations.RemoveField('profile', 'old_coach_name'),
    ]
