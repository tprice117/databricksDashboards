from rest_framework import serializers

from admin_policies.models import UserGroupPolicyMonthlyLimit


class UserGroupPolicyMonthlyLimitSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = UserGroupPolicyMonthlyLimit
        fields = "__all__"
