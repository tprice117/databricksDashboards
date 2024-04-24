from django.test import TestCase
from api.models import User, UserGroup, UserAddress, Order, OrderGroup
from datetime import date, timedelta, datetime
from api.serializers import OrderSerializer
from rest_framework.test import APIRequestFactory, force_authenticate
from admin_approvals.api.v1.views import (
    UserGroupAdminApprovalOrderViewSet,
    UserGroupAdminApprovalUserInviteViewSet,
)
from admin_approvals.models import (
    UserGroupAdminApprovalOrder,
    UserGroupAdminApprovalUserInvite,
)


class OrderApprovalTests(TestCase):
    def setUp(self):
        pass

    def test_order_approvals(self):
        """Get User with Admin Permissions and get all approvals for user.
        Get User with Member Permissions.
        Create Order for Admin User and check that the order is pending since it did not require approval.
        Create Order for Member User and check that the order status is set to approval, since it requires approval.
        Have the admin approve the order, Delete order after testing.
        """
        # Get User with Admin Permissions
        user_admin = User.objects.get(email="wickeym@gmail.com")
        print(user_admin.user_group_id)
        # Get all order approvals for User
        approvals = UserGroupAdminApprovalOrder.objects.filter(
            order__order_group__user__user_group_id=user_admin.user_group_id
        )
        print(approvals.count())
        approvals_all = UserGroupAdminApprovalOrder.objects.all()
        print(approvals_all.count())
        for approval in approvals_all:
            print(
                approval.order.order_group.user.email,
                approval.order.order_group.user.user_group_id,
            )
        # Get OrderGroup from Admin User
        order_group_admin = user_admin.ordergroup_set.first()

        # Get User with Member Permissions
        user_member = User.objects.get(email="mwickey@trydownstream.com")
        # Get OrderGroup from Member User
        order_group_member = user_member.ordergroup_set.first()

        # Create Order for Admin User
        order_admin = Order(
            order_group=order_group_admin,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=4),
        )
        order_admin.save()
        order_admin_data = OrderSerializer(order_admin).data
        order_admin_id = order_admin_data["id"]
        print("Created Admin Order", order_admin_data)
        # Check that the order is pending. This means Order did not require approval.
        self.assertEqual(order_admin_data["status"], "PENDING")

        # Create Order for Member User
        order_member = Order(
            order_group=order_group_member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=4),
        )
        order_member.save()
        order_member_data = OrderSerializer(order_member).data
        order_member_id = order_member_data["id"]
        print("Created Order", order_member_data)
        # Check that the order status is set to approval. This means Order requires approval.
        self.assertEqual(order_member_data["status"], Order.APPROVAL)

        # Have the admin approve the order

        # APPROVALS
        # user-group-admin-approval-order
        # user-group-admin-approval-user-invite

        factory = APIRequestFactory()
        view = UserGroupAdminApprovalOrderViewSet.as_view({"get": "list"})
        request = factory.get("/api/user-group-admin-approval-order/")
        force_authenticate(request, user=user_admin)
        response = view(request)
        print(response.status_code, response.data)

        api_params = {
            "order_id": order_member_id,
            "status": "APPROVED",
        }

        view = UserGroupAdminApprovalOrderViewSet.as_view({"post": "update"})
        request = factory.post("/api/user-group-admin-approval-order/", data=api_params)
        force_authenticate(request, user=user_admin)
        response = view(request, pk=order_member_id)
        print(response.status_code, response.data)

        # Delete order after testing
        order_admin.delete()
        order_member.delete()

        print("DONE")

    # def test_order_approval_outside_policies(self):
    #     # Have User create two orders outside of policies
    #     # Test that the orders are not approved

    # def test_get_order_approvals_for_usergroup(self):
    #     # Get all order approvals for UserGroup
    #     # Test that the order is in the list

    # def test_admin_approve_order(self):
    #     # Have admin approve the order
    #     # Test that the order is approved

    # def test_admin_reject_order(self):
    #     # Have admin reject the order
    #     # Test that the order is rejected

    # def test_update_approval_status(self):
    #     # Try updating the approval status
    #     # Test that it may not be changed

    # def test_add_billing_user(self):
    #     # Have admin User, Joe, add a new billing user, Joel, to the UserGroup
    #     # Test that the new user is added

    # def test_add_user_needs_approval(self):
    #     # Have member User, John, try to add a new user, Jake, to the UserGroup
    #     # Test that this needs approval

    # def test_approve_new_user(self):
    #     # Have admin User, Joe, approve the new user, Jake
    #     # Test that the new user is approved
