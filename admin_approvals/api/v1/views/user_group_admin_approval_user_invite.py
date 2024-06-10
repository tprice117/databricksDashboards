from rest_framework import viewsets

from admin_approvals.api.v1.serializers import (
    UserGroupAdminApprovalUserInviteSerializer,
)
from admin_approvals.models import UserGroupAdminApprovalUserInvite


class UserGroupAdminApprovalUserInviteViewSet(viewsets.ModelViewSet):
    queryset = UserGroupAdminApprovalUserInvite.objects.all()
    serializer_class = UserGroupAdminApprovalUserInviteSerializer

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
