from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceViewSet, FencingClassViewSet, MemberViewSet, login_view, logout_view, me,
)

router = DefaultRouter()
router.register('members', MemberViewSet, basename='member')
router.register('classes', FencingClassViewSet, basename='class')
router.register('attendance', AttendanceViewSet, basename='attendance')

urlpatterns = [
    path('me/', me),
    path('login/', login_view),
    path('logout/', logout_view),
] + router.urls
