from django.urls import path

from .views import auth, book, classes, coaches, feeds, lessons, members

urlpatterns = [
    path('login/', auth.login_view, name='login'),
    path('logout/', auth.logout_view, name='logout'),
    path('forgot-password/', auth.forgot_password, name='forgot_password'),
    path('set-password/<uidb64>/<token>/', auth.set_password, name='set_password'),

    # Classes: one sidebar item, two views sharing the filters in the URL.
    path('', classes.calendar, name='calendar'),
    path('table/', classes.class_list, name='class_list'),
    path('calendar/events/', classes.calendar_events, name='calendar_events'),
    path('classes/new/', classes.class_form, name='class_new'),
    path('classes/name/', classes.generate_name, name='generate_name'),
    path('classes/<int:pk>/', classes.class_panel, name='class_panel'),
    path('classes/<int:pk>/edit/', classes.class_form, name='class_edit'),
    path('classes/<int:pk>/move/', classes.move_class, name='class_move'),
    path('classes/<int:pk>/notes/', classes.save_notes, name='class_notes'),
    path('classes/<int:pk>/add/', classes.add_to_class, name='class_add'),
    path('classes/<int:pk>/enrol/', classes.enrol, name='class_enrol'),
    path('classes/<int:pk>/repeat/', classes.repeat, name='class_repeat'),
    path('classes/<int:pk>/delete/', classes.delete_class, name='class_delete'),
    path('attendance/<int:pk>/status/', classes.set_status, name='attendance_status'),
    path('attendance/<int:pk>/remove/', classes.remove_from_class, name='attendance_remove'),
    path('lesson-requests/<int:pk>/', lessons.request_panel, name='lesson_request_panel'),
    path('lesson-requests/<int:pk>/<verb>/', lessons.answer, name='lesson_request_answer'),

    # Calendar sync, for everyone. The feed itself needs no login: its token is the key.
    path('calendar-sync/', feeds.calendar_sync, name='calendar_sync'),
    path('calendar-sync/reset/', feeds.reset_feed, name='calendar_feed_reset'),
    path('calendar/<str:token>.ics', feeds.calendar_feed, name='calendar_feed'),

    # A member's own pages.
    path('book/', book.book, name='book'),
    path('book/<int:pk>/', book.book_class, name='book_class'),
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
