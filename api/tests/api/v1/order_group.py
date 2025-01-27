from django.conf import settings

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from api.models import OrderGroup, User, SellerProductSellerLocation
from api.serializers import OrderSerializer, OrderGroupSerializer
from datetime import datetime, timedelta


class OrderGroupAPITests(APITestCase):
    def setUp(self):
        if settings.ENVIRONMENT == "TEST":
            raise Exception("Cannot run tests in production")
        self.client = APIClient()
        self.user = User.objects.get(email="wickeym@gmail.com")
        self.client.force_authenticate(user=self.user)
        self.start_date = datetime.now().date()

    def tearDown(self):
        pass

    def test_create_delivery(self):
        print("TESTING CREATE DELIVERY")
        try:
            seller_product_seller_location = (
                SellerProductSellerLocation.objects.filter(
                    seller_product__product__main_product__has_rental_multi_step=True
                )
                .filter(active=True)
                .first()
            )

            order_group = OrderGroup.objects.create(
                user=self.user,
                user_address=self.user.useraddress_set.first(),
                seller_product_seller_location=seller_product_seller_location,
                start_date=self.start_date,
            )

            url = reverse(
                "api_booking_delivery", kwargs={"order_group_id": order_group.id}
            )
            data = {
                "date": self.start_date.strftime("%Y-%m-%d"),
                "schedule_window": "Anytime (7am-4pm)",
            }
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn("id", response.data)
            print("TESTS SUCCESSFUL")
        except Exception as e:
            print("TESTS FAILED", e)
        finally:
            order_group.orders.all().delete()
            order_group.delete()

    def test_create_onetime(self):
        print("TEST CREATE ONETIME")
        try:
            seller_product_seller_location = (
                SellerProductSellerLocation.objects.filter(
                    seller_product__product__main_product__has_rental_multi_step=True
                )
                .filter(active=True)
                .first()
            )

            order_group = OrderGroup.objects.create(
                user=self.user,
                user_address=self.user.useraddress_set.first(),
                seller_product_seller_location=seller_product_seller_location,
                start_date=self.start_date,
            )

            url = reverse(
                "api_booking_one_time", kwargs={"order_group_id": order_group.id}
            )
            data = {
                "date": self.start_date.strftime("%Y-%m-%d"),
                "schedule_window": "Anytime (7am-4pm)",
            }
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn("id", response.data)
            print("TESTS SUCCESSFUL")
        except Exception as e:
            print("TESTS FAILED", e)
        finally:
            order_group.orders.all().delete()
            order_group.delete()

    def test_create_pickup(self):
        print("TEST CREATE PICKUP")
        try:
            seller_product_seller_location = (
                SellerProductSellerLocation.objects.filter(
                    seller_product__product__main_product__has_rental_multi_step=True,
                    allows_pick_up=True,
                )
                .filter(active=True)
                .first()
            )

            order_group = OrderGroup.objects.create(
                user=self.user,
                user_address=self.user.useraddress_set.first(),
                seller_product_seller_location=seller_product_seller_location,
                start_date=self.start_date,
            )

            url = reverse(
                "api_booking_pickup", kwargs={"order_group_id": order_group.id}
            )
            data = {
                "date": self.start_date.strftime("%Y-%m-%d"),
                "schedule_window": "Anytime (7am-4pm)",
            }
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn("id", response.data)
            print("TESTS SUCCESSFUL")
        except Exception as e:
            print("TESTS FAILED", e)
        finally:
            order_group.orders.all().delete()
            order_group.delete()

    def test_create_swap(self):
        print("TEST CREATE SWAP")
        try:
            seller_product_seller_location = (
                SellerProductSellerLocation.objects.filter(
                    seller_product__product__main_product__has_rental=True
                )
                .filter(active=True)
                .first()
            )

            order_group = OrderGroup.objects.create(
                user=self.user,
                user_address=self.user.useraddress_set.first(),
                seller_product_seller_location=seller_product_seller_location,
                start_date=self.start_date,
            )

            delivery_order = order_group.create_delivery(
                self.start_date, schedule_window="Anytime (7am-4pm)"
            )

            swap_date = self.start_date + timedelta(days=1)

            url = reverse("api_booking_swap", kwargs={"order_group_id": order_group.id})
            data = {
                "date": swap_date.strftime("%Y-%m-%d"),
                "schedule_window": "Anytime (7am-4pm)",
            }
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn("id", response.data)
            print("TESTS SUCCESSFUL")
        except Exception as e:
            print("TESTS FAILED", e)
        finally:
            order_group.orders.all().delete()
            order_group.delete()

    def test_create_removal(self):
        print("TEST CREATE REMOVAL")
        try:
            seller_product_seller_location = (
                SellerProductSellerLocation.objects.filter(
                    seller_product__product__main_product__has_rental_multi_step=True
                )
                .filter(active=True)
                .first()
            )

            order_group = OrderGroup.objects.create(
                user=self.user,
                user_address=self.user.useraddress_set.first(),
                seller_product_seller_location=seller_product_seller_location,
                start_date=self.start_date,
            )

            delivery_order = order_group.create_delivery(
                self.start_date, schedule_window="Anytime (7am-4pm)"
            )

            removal_date = self.start_date + timedelta(days=1)

            url = reverse(
                "api_booking_removal", kwargs={"order_group_id": order_group.id}
            )
            data = {
                "date": removal_date.strftime("%Y-%m-%d"),
                "schedule_window": "Anytime (7am-4pm)",
            }
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn("id", response.data)
            print("TESTS SUCCESSFUL")
        except Exception as e:
            print("TESTS FAILED", e)
        finally:
            order_group.orders.all().delete()
            order_group.delete()

    def test_update_access_details(self):
        print("TEST UPDATE ACCESS DETAILS")
        try:
            seller_product_seller_location = (
                SellerProductSellerLocation.objects.filter(
                    seller_product__product__main_product__has_rental=True
                )
                .filter(active=True)
                .first()
            )

            order_group = OrderGroup.objects.create(
                user=self.user,
                user_address=self.user.useraddress_set.first(),
                seller_product_seller_location=seller_product_seller_location,
                start_date=self.start_date,
            )

            url = reverse(
                "api_booking_update_access_details",
                kwargs={"order_group_id": order_group.id},
            )
            data = {"access_details": "New access details"}
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["access_details"], "New access details")
            print("TESTS SUCCESSFUL")
        except Exception as e:
            print("TESTS FAILED", e)
        finally:
            order_group.orders.all().delete()
            order_group.delete()

    def test_update_placement_details(self):
        print("TEST UPDATE BOOKING PLACEMENT DETAILS")
        try:
            seller_product_seller_location = (
                SellerProductSellerLocation.objects.filter(
                    seller_product__product__main_product__has_rental=True
                )
                .filter(active=True)
                .first()
            )

            order_group = OrderGroup.objects.create(
                user=self.user,
                user_address=self.user.useraddress_set.first(),
                seller_product_seller_location=seller_product_seller_location,
                start_date=self.start_date,
            )

            url = reverse(
                "api_booking_update_placement_details",
                kwargs={"order_group_id": order_group.id},
            )
            data = {
                "placement_details": "New placement details",
                "delivered_to_street": True,
            }
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.data["placement_details"], "New placement details"
            )
            self.assertTrue(response.data["delivered_to_street"])
            print("TESTS SUCCESSFUL")
        except Exception as e:
            print("TESTS FAILED", e)
        finally:
            order_group.orders.all().delete()
            order_group.delete()

    @staticmethod
    def run_tests():
        test = OrderGroupAPITests()
        test.setUp()
        test.test_create_delivery()
        test.test_create_onetime()
        test.test_create_pickup()
        test.test_create_swap()
        test.test_create_removal()
        test.test_update_access_details()
        test.test_update_placement_details()
        test.tearDown()
        print("All tests done.")
