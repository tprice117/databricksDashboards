from rest_framework import viewsets

from admin_policies.api.v1.serializers import UserGroupPolicyPurchaseApprovalSerializer
from admin_policies.models import UserGroupPolicyPurchaseApproval

# from api.models import User


class UserGroupPolicyPurchaseApprovalViewSet(viewsets.ModelViewSet):
    queryset = UserGroupPolicyPurchaseApproval.objects.all()
    serializer_class = UserGroupPolicyPurchaseApprovalSerializer

    def get_queryset(self):
        is_superuser = self.request.user == "ALL" or (
            self.request.user.user_group.is_superuser
            if self.request.user and self.request.user.user_group
            else False
        )
        if is_superuser:
            return self.queryset
        else:
            return self.queryset.filter(user_group_id=self.request.user.user_group_id)
