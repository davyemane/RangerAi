from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sites', views.TouristicSiteViewSet)
router.register(r'services', views.ServiceViewSet)
router.register(r'eco-actions', views.EcoActionViewSet)
router.register(r'profiles', views.UserProfileViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]