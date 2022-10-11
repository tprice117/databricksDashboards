from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api import views

router = routers.DefaultRouter()
router.register(r'orders', views.OrderViewSet, 'api')
router.register(r'contacts', views.ContactViewSet, 'api')
router.register(r'accounts', views.AccountViewSet, 'api')
router.register(r'account-contacts', views.AccountContactRelationViewSet, 'api')
router.register(r'opportunities', views.OpportunityViewSet, 'api')
router.register(r'product-categories', views.ProductCategoryViewSet, 'api')
router.register(r'product-category-infos', views.ProductCategoryInfoViewSet, 'api')
router.register(r'main-products', views.MainProductViewSet, 'api')
router.register(r'main-product-infos', views.MainProductInfoViewSet, 'api')
router.register(r'products', views.ProductViewSet, 'api')
router.register(r'main-product-frequencies', views.MainProductFrequencyViewSet, 'api')
router.register(r'price-books', views.PriceBookViewSet, 'api')
router.register(r'price-book-entries', views.PriceBookEntryViewSet, 'api')
router.register(r'main-product-add-ons', views.MainProductAddOnViewSet, 'api')
router.register(r'main-product-add-on-choices', views.MainProductAddOnChoiceViewSet, 'api')

urlpatterns = [
    path('api/', include(router.urls)),
    # path('admin/', admin.site.urls),
    path('api/tasks/<int:pk>', views.TaskView.as_view()),
    path('api/tasks/', views.TaskView.as_view()),
    path('api/agents/<int:pk>', views.AgentView.as_view()),
    path('api/agents/', views.AgentView.as_view()),
    path('api/teams/<int:pk>', views.TeamView.as_view()),
    path('api/teams/', views.TeamView.as_view()),
    # path('manager/<int:pk>', views.ManagerView.as_view()),
    # path('manager/', views.ManagerView.as_view()),
    path('api/customers/<int:pk>', views.CustomerView.as_view()),
    path('api/customers/', views.CustomerView.as_view()),
    # path('merchant/<int:pk>', views.MerchantView.as_view()),
    # path('merchant/', views.MerchantView.as_view()),
    # path('mission/<int:pk>', views.MissionView.as_view()),
    # path('mission/', views.MissionView.as_view()),
    path('api/convert-sf-order-to-scrap-task/<str:pk>', views.ConvertSFOrderToScrapTask.as_view())
]