from rest_framework.routers import DefaultRouter

from .views import BookViewSetV1

router = DefaultRouter()
router.register(r"books", BookViewSetV1)


urlpatterns = router.urls
