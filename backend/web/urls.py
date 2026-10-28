from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('set-password/<uidb64>/<token>/', views.set_password, name='set_password'),

    # Classes: one sidebar item, two views sharing the filters in the URL.
    path('', views.calendar, name='calendar'),
    path('table/', views.class_table, name='class_table'),
    path('calendar/events/', views.calendar_events, name='calendar_events'),
    path('classes/new/', views.class_form, name='class_new'),
    path('classes/name/', views.generate_name, name='generate_name'),
    path('classes/<int:pk>/', views.class_panel, name='class_panel'),
    path('classes/<int:pk>/edit/', views.class_form, name='class_edit'),
    path('classes/<int:pk>/move/', views.move_class, name='class_move'),
    path('classes/<int:pk>/notes/', views.save_notes, name='class_notes'),
    path('classes/<int:pk>/add/', views.add_to_class, name='class_add'),
    path('classes/<int:pk>/enrol/', views.enrol, name='class_enrol'),
    path('classes/<int:pk>/repeat/', views.repeat, name='class_repeat'),
    path('classes/<int:pk>/delete/', views.delete_class, name='class_delete'),
    path('attendance/<int:pk>/status/', views.set_status, name='attendance_status'),
    path('attendance/<int:pk>/remove/', views.remove_from_class, name='attendance_remove'),
    path('lesson-requests/<int:pk>/', views.lesson_request_panel, name='lesson_request_panel'),
    path('lesson-requests/<int:pk>/<verb>/', views.answer_request, name='lesson_request_answer'),

    # A member's own pages.
    path('book/', views.book, name='book'),
    path('book/<int:pk>/', views.book_class, name='book_class'),
    path('lessons/', views.lessons, name='lessons'),
    path('lessons/events/', views.lesson_events, name='lesson_events'),
    path('lessons/new/', views.request_lesson, name='lesson_new'),
    path('lessons/<int:pk>/cancel/', views.cancel_lesson, name='lesson_cancel'),
    path('profile/', views.profile, name='profile'),

    # Managers.
    path('members/', views.member_list, name='members'),
    path('members/new/', views.member_form, name='member_new'),
    path('members/<int:pk>/', views.member_panel, name='member_panel'),
    path('members/<int:pk>/edit/', views.member_form, name='member_edit'),
    path('coaches/', views.coach_list, name='coaches'),
    path('coaches/new/', views.coach_form, name='coach_new'),
    path('coaches/<int:pk>/', views.coach_page, name='coach'),
    path('coaches/<int:pk>/edit/', views.coach_form, name='coach_edit'),
    path('members/<int:pk>/invite/', views.invite, {'kind': 'member'}, name='member_invite'),
    path('coaches/<int:pk>/invite/', views.invite, {'kind': 'coach'}, name='coach_invite'),
    path('logins/<int:pk>/active/', views.set_login_active, name='login_active'),
]
