from rest_framework import serializers

from admin_approvals.models import UserGroupAdminApprovalOrder


class UserGroupAdminApprovalOrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserGroupAdminApprovalOrder
        fields = "__all__"
