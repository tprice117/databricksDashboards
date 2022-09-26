from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api import views

router = routers.DefaultRouter()
router.register(r'orders', views.OrderViewSet, 'api')
router.register(r'accounts', views.AccountViewSet, 'api')
router.register(r'opportunities', views.OpportunityViewSet, 'api')
router.register(r'product-categories', views.ProductCategoryViewSet, 'api')
router.register(r'product-category-infos', views.ProductCategoryInfoViewSet, 'api')
router.register(r'main-products', views.MainProductViewSet, 'api')
router.register(r'main-product-infos', views.MainProductInfoViewSet, 'api')
router.register(r'products', views.ProductViewSet, 'api')
router.register(r'main-product-frequencies', views.MainProductFrequencyViewSet, 'api')

urlpatterns = [
    path('api/', include(router.urls)),
    # path('admin/', admin.site.urls),
    # path('task/<int:pk>', views.TaskView.as_view()),
    # path('task/', views.TaskView.as_view()),
    # path('agent/<int:pk>', views.AgentView.as_view()),
    # path('agent/', views.AgentView.as_view()),
    # path('team/<int:pk>', views.TeamView.as_view()),
    # path('team/', views.TeamView.as_view()),
    # path('manager/<int:pk>', views.ManagerView.as_view()),
    # path('manager/', views.ManagerView.as_view()),
    # path('customer/<int:pk>', views.CustomerView.as_view()),
    # path('customer/', views.CustomerView.as_view()),
    # path('merchant/<int:pk>', views.MerchantView.as_view()),
    # path('merchant/', views.MerchantView.as_view()),
    # path('mission/<int:pk>', views.MissionView.as_view()),
    # path('mission/', views.MissionView.as_view()),
]