from rest_framework import serializers

from admin_policies.models import UserGroupPolicyInvitationApproval


class UserGroupPolicyInvitationApprovalSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserGroupPolicyInvitationApproval
        fields = [
            "id",
            "user_type",
        ]
