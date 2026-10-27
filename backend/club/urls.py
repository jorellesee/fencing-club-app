from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceViewSet, CoachViewSet, FencingClassViewSet, LessonRequestViewSet, LoginViewSet,
    MemberViewSet, login_view, logout_view, me, password_reset_view, set_password_view,
)

router = DefaultRouter()
router.register('members', MemberViewSet, basename='member')
router.register('coaches', CoachViewSet, basename='coach')
router.register('classes', FencingClassViewSet, basename='class')
router.register('attendance', AttendanceViewSet, basename='attendance')
router.register('lesson-requests', LessonRequestViewSet, basename='lesson-request')
router.register('logins', LoginViewSet, basename='login')

urlpatterns = [
    path('me/', me),
    path('login/', login_view),
    path('logout/', logout_view),
    path('password-reset/', password_reset_view),
    path('set-password/<uidb64>/<token>/', set_password_view),
] + router.urls
