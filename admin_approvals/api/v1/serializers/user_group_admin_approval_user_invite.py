from rest_framework import serializers

from admin_approvals.models import UserGroupAdminApprovalUserInvite


class UserGroupAdminApprovalUserInviteSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserGroupAdminApprovalUserInvite
        fields = "__all__"
