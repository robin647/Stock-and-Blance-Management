from rest_framework.routers import DefaultRouter

from .views import ShowroomViewSet

router = DefaultRouter()
router.register("", ShowroomViewSet, basename="showroom")

urlpatterns = router.urls
