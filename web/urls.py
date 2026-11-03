from django.urls import path

from .views import auth, book, coaches, feeds, lessons, members, sessions

urlpatterns = [
    path('login/', auth.login_view, name='login'),
    path('logout/', auth.logout_view, name='logout'),
    path('forgot-password/', auth.forgot_password, name='forgot_password'),
    path('set-password/<uidb64>/<token>/', auth.set_password, name='set_password'),

    # Sessions: one sidebar item, two views sharing the filters in the URL.
    path('', sessions.calendar, name='calendar'),
    path('table/', sessions.session_list, name='session_list'),
    path('calendar/events/', sessions.calendar_events, name='calendar_events'),
    path('sessions/new/', sessions.session_form, name='session_new'),
    path('sessions/name/', sessions.generate_name, name='generate_name'),
    path('sessions/<int:pk>/', sessions.session_panel, name='session_panel'),
    path('sessions/<int:pk>/edit/', sessions.session_form, name='session_edit'),
    path('sessions/<int:pk>/move/', sessions.move_session, name='session_move'),
    path('sessions/<int:pk>/notes/', sessions.save_notes, name='session_notes'),
    path('sessions/<int:pk>/add/', sessions.add_to_session, name='session_add'),
    path('sessions/<int:pk>/enrol/', sessions.enrol, name='session_enrol'),
    path('sessions/<int:pk>/repeat/', sessions.repeat, name='session_repeat'),
    path('sessions/<int:pk>/delete/', sessions.delete_session, name='session_delete'),
    path('attendance/<int:pk>/status/', sessions.set_status, name='attendance_status'),
    path('attendance/<int:pk>/remove/', sessions.remove_from_session, name='attendance_remove'),
    path('lesson-requests/<int:pk>/', lessons.request_panel, name='lesson_request_panel'),
    path('lesson-requests/<int:pk>/<verb>/', lessons.answer, name='lesson_request_answer'),

    # Calendar sync, for everyone. The feed itself needs no login: its token is the key.
    path('calendar-sync/', feeds.calendar_sync, name='calendar_sync'),
    path('calendar-sync/reset/', feeds.reset_feed, name='calendar_feed_reset'),
    path('calendar/<str:token>.ics', feeds.calendar_feed, name='calendar_feed'),

    # A member's own pages.
    path('book/', book.book, name='book'),
    path('book/<int:pk>/', book.book_session, name='book_session'),
    path('lessons/', lessons.lessons, name='lessons'),
    path('lessons/events/', lessons.lesson_events, name='lesson_events'),
    path('lessons/new/', lessons.request_lesson, name='lesson_new'),
    path('lessons/<int:pk>/cancel/', lessons.cancel_lesson, name='lesson_cancel'),
    path('profile/', members.profile, name='profile'),

    # Managers.
    path('members/', members.member_list, name='members'),
    path('members/new/', members.member_form, name='member_new'),
    path('members/<int:pk>/', members.member_panel, name='member_panel'),
    path('members/<int:pk>/edit/', members.member_form, name='member_edit'),
    path('coaches/', coaches.coach_list, name='coaches'),
    path('coaches/new/', coaches.coach_form, name='coach_new'),
    path('coaches/<int:pk>/', coaches.coach_panel, name='coach_panel'),
    path('coaches/<int:pk>/edit/', coaches.coach_form, name='coach_edit'),
    path('members/<int:pk>/invite/', coaches.invite, {'kind': 'member'}, name='member_invite'),
    path('coaches/<int:pk>/invite/', coaches.invite, {'kind': 'coach'}, name='coach_invite'),
    path('logins/<int:pk>/active/', coaches.set_login_active, name='login_active'),
]
