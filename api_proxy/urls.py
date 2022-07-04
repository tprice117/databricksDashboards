from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api import views

router = routers.DefaultRouter()
# router.register(r'scrappers', views.ScrapperView, 'api')
# router.register(r'agents', views.Agents, 'api')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('task/<int:pk>', views.TaskView.as_view()),
    path('task/', views.TaskView.as_view()),
    path('agent/<int:pk>', views.AgentView.as_view()),
    path('agent/', views.AgentView.as_view()),
    path('team/<int:pk>', views.TeamView.as_view()),
    path('team/', views.TeamView.as_view()),
    path('manager/<int:pk>', views.ManagerView.as_view()),
    path('manager/', views.ManagerView.as_view()),
    path('customer/<int:pk>', views.CustomerView.as_view()),
    path('customer/', views.CustomerView.as_view()),
    path('merchant/<int:pk>', views.MerchantView.as_view()),
    path('merchant/', views.MerchantView.as_view()),
    path('mission/<int:pk>', views.MissionView.as_view()),
    path('mission/', views.MissionView.as_view()),
]