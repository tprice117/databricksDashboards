from django.test import TestCase
from api.models import User, UserGroup, UserAddress, Order, OrderGroup
from datetime import date, timedelta, datetime
from api.serializers import OrderSerializer
from admin_approvals.api.v1.serializers import (
    UserGroupAdminApprovalUserInviteSerializer,
)
from rest_framework.test import APIRequestFactory, force_authenticate
from admin_approvals.api.v1.views import (
    UserGroupAdminApprovalOrderViewSet,
    UserGroupAdminApprovalUserInviteViewSet,
)
from admin_approvals.models import (
    UserGroupAdminApprovalOrder,
    UserGroupAdminApprovalUserInvite,
)
from common.models.choices.approval_status import ApprovalStatus


class UserInviteApprovalTests(TestCase):
    def setUp(self):
        pass

    def test_user_invite_approvals(self):
        """Get User with Admin Permissions and get all approvals for user.
        Get User with Member Permissions.
        Create User Invite for Admin User and check that the User is created since it did not require approval.
        Create User Invite for Member User and check that a UserInvite was created, since it requires approval.
        Have the admin approve the invitation, Delete users after testing.
        """
        factory = APIRequestFactory()

        # Get User with Admin Permissions
        user_admin = User.objects.get(email="wickeym@gmail.com")
        # Get User with Member Permissions
        user_member = User.objects.get(email="mwickey@trydownstream.com")

        # ===================================
        # Create UserInvite for Admin User
        admin_invite_params = {
            "user_group": str(user_admin.user_group_id),
            "email": "wickeym@icloud.com",
            "created_by": str(user_admin.id),
        }
        view = UserGroupAdminApprovalUserInviteViewSet.as_view({"post": "create"})
        request = factory.post(
            "/api/user-address/", data=admin_invite_params, format="json"
        )
        force_authenticate(request, user=user_admin)
        admin_invite_response = view(request, pk=str(user_admin.id))
        print(
            f"Admin Invited/Created User: [{admin_invite_response.status_code}] {admin_invite_response.data}"
        )

        added_by_admin_user = User.objects.filter(
            email=admin_invite_params["email"]
        ).first()
        # Check that the order is pending. This means Order did not require approval.
        self.assertIsNotNone(added_by_admin_user)
        # Delete after testing
        invite_admin = UserGroupAdminApprovalUserInvite.objects.filter(
            id=admin_invite_response.data["id"]
        ).first()
        invite_admin.user.delete()
        invite_admin.delete()

        # ===================================
        # Create UserInvite for Member User
        member_invite_params = {
            "user_group": str(user_member.user_group_id),
            "email": "wickeym@yahoo.com",
            "created_by": str(user_member.id),
        }
        view = UserGroupAdminApprovalUserInviteViewSet.as_view({"post": "create"})
        request = factory.post(
            "/api/user-address/", data=member_invite_params, format="json"
        )
        force_authenticate(request, user=user_member)
        member_invite_response = view(request, pk=str(user_member.id))
        print(
            f"Created User Invitation: [{member_invite_response.status_code}] {member_invite_response.data}"
        )

        # Check that the order status is set to approval. This means Order requires approval.
        self.assertEqual(member_invite_response.data["status"], Order.Status.PENDING)

        # # List all invitation approvals for the admin user.
        # view = UserGroupAdminApprovalUserInviteViewSet.as_view({"get": "list"})

        # request = factory.get("/api/user-group-admin-approval-user-invite/")
        # force_authenticate(request, user=user_admin)
        # response = view(request)
        # print(response.status_code, response.data)

        # Have the admin approve the user invite via API
        api_params = {
            "id": member_invite_response.data["id"],
            "email": member_invite_response.data["email"],
            "status": ApprovalStatus.APPROVED,
            "user_group": member_invite_response.data["user_group"],
            "created_by": member_invite_response.data["created_by"],
        }

        view = UserGroupAdminApprovalUserInviteViewSet.as_view({"post": "update"})
        request = factory.post(
            "/api/user-group-admin-approval-user-invite/", data=api_params
        )
        force_authenticate(request, user=user_admin)
        response = view(request, pk=member_invite_response.data["id"])
        print(response.status_code, response.data)
        # 400 {'type': <ErrorType.VALIDATION_ERROR: 'validation_error'>, 'errors': [{'code': 'unique', 'detail': 'The fields user_group, email must make a unique set.', 'attr': 'non_field_errors'}]}

        added_by_member_user = User.objects.filter(
            email=member_invite_params["email"]
        ).first()
        self.assertIsNotNone(added_by_member_user)

        # Delete after testing
        invite_member = UserGroupAdminApprovalUserInvite.objects.filter(
            id=member_invite_response.data["id"]
        ).first()
        invite_member.user.delete()
        invite_member.delete()

        print("TESTS SUCCESSFUL")


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
        print("Created Admin Order", order_admin_data)
        # Check that the order is pending. This means Order did not require approval.
        self.assertEqual(order_admin_data["status"], Order.Status.PENDING)

        # Ensure policy is lower than order amount so that it requires approval.
        purchase_policy = user_member.user_group.policy_purchase_approvals.filter(
            user_type=user_member.type
        ).first()
        # The order below is $184, so it should require approval.
        purchase_policy.amount = 100
        purchase_policy.save()

        # Create Order for Member User
        order_member = Order(
            order_group=order_group_member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=4),
        )
        order_member.save()
        order_member_data = OrderSerializer(order_member).data
        print("============================")
        print("Created Order", order_member_data)
        # Check that the order status is set to approval. This means Order requires approval.
        self.assertEqual(order_member_data["status"], Order.Status.APPROVAL)

        # Ensure policy is higher than order amount so that it doesn't require approval.
        purchase_policy = user_member.user_group.policy_purchase_approvals.filter(
            user_type=user_member.type
        ).first()
        purchase_policy.amount = 1000
        purchase_policy.save()

        # Create Order for Member User
        order_member2 = Order(
            order_group=order_group_member,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=4),
        )
        order_member2.save()
        order_member2_data = OrderSerializer(order_member2).data
        print("============================")
        print("Created Order 2", order_member2_data)
        # Check that the order status is set to approval. This means Order requires approval.
        self.assertEqual(order_member2_data["status"], Order.Status.PENDING)

        # Have the admin approve the order

        # APPROVALS
        # user-group-admin-approval-order
        # user-group-admin-approval-user-invite

        factory = APIRequestFactory()
        view = UserGroupAdminApprovalOrderViewSet.as_view({"get": "list"})
        request = factory.get("/api/user-group-admin-approval-order/")
        force_authenticate(request, user=user_admin)
        response_list = view(request)
        print("============================")
        print(response_list.status_code, response_list.data)

        api_params = {
            "order": response_list.data[0]["order"],
            "status": "APPROVED",
        }

        view = UserGroupAdminApprovalOrderViewSet.as_view({"post": "update"})
        request = factory.post("/api/user-group-admin-approval-order/", data=api_params)
        force_authenticate(request, user=user_admin)
        response = view(request, pk=response_list.data[0]["id"])
        print("============================")
        print(response.status_code, response.data)

        # Delete order after testing
        order_admin.delete()
        order_member.delete()
        order_member2.delete()

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
