# from django.conf.urls import *
from rest_framework.routers import DefaultRouter

from .views import UserGroupAdminApprovalOrderViewSet
from .views import UserGroupAdminApprovalUserInviteViewSet

router = DefaultRouter()
router.register(r"usergroup-admin-approval-order", UserGroupAdminApprovalOrderViewSet)
router.register(
    r"usergroup-admin-approval-user-invite", UserGroupAdminApprovalUserInviteViewSet
)
urlpatterns = router.urls
