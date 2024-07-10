from rest_framework import serializers

from admin_approvals.models import UserGroupAdminApprovalUserInvite
from api.serializers import UserSerializer


class UserGroupAdminApprovalUserInviteSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)
    user = UserSerializer(read_only=True, required=False, allow_null=True)
    redirect_url = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserGroupAdminApprovalUserInvite
        fields = "__all__"
