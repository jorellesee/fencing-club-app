"""FencingClass becomes TrainingSession, and LessonRequest is folded into it.

Written by hand: makemigrations would ask whether FencingClass was renamed, and a
rename keeps every class's id, roster and calendar feed UID. Pending requests
become unconfirmed individual sessions (capacity 1) with the member on them,
accepted ones make sure their class has capacity 1, and declined or cancelled
ones are dropped.
"""
from django.db import migrations, models
import django.db.models.deletion


def merge_lesson_requests(apps, schema_editor):
    LessonRequest = apps.get_model('club', 'LessonRequest')
    TrainingSession = apps.get_model('club', 'TrainingSession')
    Attendance = apps.get_model('club', 'Attendance')
    for lesson in LessonRequest.objects.select_related('member'):
        if lesson.status == 'accepted' and lesson.fencing_class_id:
            TrainingSession.objects.filter(pk=lesson.fencing_class_id).update(capacity=1)
        elif lesson.status == 'pending':
            session = TrainingSession.objects.create(
                name=f'Private lesson: {lesson.member.name}',
                start=lesson.start,
                end=lesson.end,
                coach_id=lesson.coach_id,
                weapon=lesson.member.weapon,
                capacity=1,
                notes=lesson.note,
                status='unconfirmed',
            )
            Attendance.objects.create(session=session, member=lesson.member, status='enrolled')


def split_lesson_requests(apps, schema_editor):
    """Going back: individual sessions become requests again, so nothing pending
    is lost. Declined and cancelled requests can't come back. A coached group
    class someone capped at 1 comes back as an accepted request for its member."""
    LessonRequest = apps.get_model('club', 'LessonRequest')
    TrainingSession = apps.get_model('club', 'TrainingSession')
    for session in TrainingSession.objects.filter(capacity=1, coach__isnull=False):
        row = session.attendance.first()
        if row is None:
            continue
        confirmed = session.status == 'confirmed'
        LessonRequest.objects.create(
            member_id=row.member_id,
            coach_id=session.coach_id,
            start=session.start,
            end=session.end,
            note=session.notes,
            status='accepted' if confirmed else 'pending',
            fencing_class=session if confirmed else None,
        )
        if not confirmed:
            session.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('club', '0011_calendarfeed'),
    ]

    operations = [
        migrations.RenameModel('FencingClass', 'TrainingSession'),
        migrations.AlterModelOptions(name='trainingsession', options={'ordering': ['start']}),
        migrations.AlterField(
            model_name='trainingsession',
            name='coach',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='sessions', to='club.coach',
            ),
        ),
        migrations.AddField(
            model_name='trainingsession',
            name='category',
            field=models.CharField(
                choices=[('fencing', 'Fencing'), ('conditioning', 'Physical conditioning')],
                default='fencing', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='trainingsession',
            name='status',
            field=models.CharField(
                choices=[('unconfirmed', 'Unconfirmed'), ('confirmed', 'Confirmed')],
                default='confirmed', max_length=12,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='attendance', name='one_attendance_per_member_per_class',
        ),
        migrations.RenameField('attendance', 'fencing_class', 'session'),
        migrations.AddConstraint(
            model_name='attendance',
            constraint=models.UniqueConstraint(
                fields=('session', 'member'), name='one_attendance_per_member_per_session',
            ),
        ),
        migrations.AlterField(
            model_name='profile',
            name='coach',
            field=models.OneToOneField(
                blank=True, help_text='Coaches only: whose sessions this login can mark.',
                null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='profile', to='club.coach',
            ),
        ),
        migrations.RunPython(merge_lesson_requests, split_lesson_requests),
        migrations.DeleteModel(name='LessonRequest'),
    ]
