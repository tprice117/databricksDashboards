from django.conf import settings

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from api.models import OrderGroup, User, SellerProductSellerLocation
from api.serializers import OrderSerializer, OrderGroupSerializer
from datetime import datetime, timedelta


class OrderAPITests(APITestCase):
    def setUp(self):
        if settings.ENVIRONMENT == "TEST":
            raise Exception("Cannot run tests in production")
        self.client = APIClient()
        self.user = User.objects.get(email="wickeym@gmail.com")
        self.client.force_authenticate(user=self.user)
        self.start_date = datetime.now().date()

    def tearDown(self):
        pass

    def test_cancel_order(self):
        print("TESTING CANCEL ORDER")
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

            url = reverse("api_order_cancel", kwargs={"order_id": delivery_order.id})
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("id", response.data)
            print("TESTS SUCCESSFUL")
        except Exception as e:
            print("TESTS FAILED", e)
        finally:
            order_group.delete()

    def test_reschedule_order(self):
        print("TESTING RESCEDULE ORDER")
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

            url = reverse(
                "api_order_reschedule", kwargs={"order_id": delivery_order.id}
            )
            new_date = self.start_date + timedelta(days=1)
            data = {"date": new_date.strftime("%Y-%m-%d")}
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("id", response.data)
            print("TESTS SUCCESSFUL")
        except Exception as e:
            print("TESTS FAILED", e)
        finally:
            order_group.delete()

    @staticmethod
    def run_tests():
        test = OrderAPITests()
        test.setUp()
        test.test_cancel_order()
        test.test_reschedule_order()
        test.tearDown()
        print("All tests done.")
