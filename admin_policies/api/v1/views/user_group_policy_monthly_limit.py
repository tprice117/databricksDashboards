from rest_framework import viewsets

from admin_policies.api.v1.serializers import UserGroupPolicyMonthlyLimitSerializer
from admin_policies.models import UserGroupPolicyMonthlyLimit


class UserGroupPolicyMonthlyLimitViewSet(viewsets.ModelViewSet):
    queryset = UserGroupPolicyMonthlyLimit.objects.all()
    serializer_class = UserGroupPolicyMonthlyLimitSerializer

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
