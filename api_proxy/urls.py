from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api import views

router = routers.DefaultRouter()
# router.register(r'scrappers', views.ScrapperView, 'api')
# router.register(r'agents', views.Agents, 'api')

urlpatterns = [
    path('admin/', admin.site.urls),
    path("task/", views.Task, name="task"),
    path("agent/", views.Agent, name="agent"),
    path("team/", views.Team, name="team"),
    path("manager/", views.Manager, name="manager"),
    path("customer/", views.Customer, name="customer"),
    path("user/", views.User, name="user"),
    path("merchant/", views.Merchant, name="merchant"),
    path("mission/", views.Mission, name="mission"),
    path("geofence/", views.Geofence, name="geofence"),
]