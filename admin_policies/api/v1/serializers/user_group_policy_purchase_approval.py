from rest_framework import serializers

from admin_policies.models import UserGroupPolicyPurchaseApproval


class UserGroupPolicyPurchaseApprovalSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserGroupPolicyPurchaseApproval
        fields = [
            "id",
            "user_type",
            "amount",
        ]
