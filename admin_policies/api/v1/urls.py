# from django.conf.urls import *
from rest_framework.routers import DefaultRouter

from .views import UserGroupPolicyPurchaseApprovalViewSet
from .views import UserGroupPolicyMonthlyLimitViewSet
from .views import UserGroupPolicyInvitationApprovalViewSet

router = DefaultRouter()
router.register(
    r"usergroup-policy-purchase-approval", UserGroupPolicyPurchaseApprovalViewSet
)
router.register(r"usergroup-policy-monthly-limit", UserGroupPolicyMonthlyLimitViewSet)
router.register(
    r"usergroup-policy-invitation-approval", UserGroupPolicyInvitationApprovalViewSet
)
urlpatterns = router.urls
