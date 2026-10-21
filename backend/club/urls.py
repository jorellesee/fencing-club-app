from rest_framework.routers import DefaultRouter

from .views import AttendanceViewSet, FencingClassViewSet, MemberViewSet

router = DefaultRouter()
router.register('members', MemberViewSet, basename='member')
router.register('classes', FencingClassViewSet, basename='class')
router.register('attendance', AttendanceViewSet, basename='attendance')

urlpatterns = router.urls
