from django.test import TestCase
from api.models import Order
import notifications.signals


class NotificationTests(TestCase):

    def test_order_notifications(
            self,
            test_order_id="01c3f60f-6389-4acc-b67a-591e8dac8e5d",
            test_email="mwickey@trydownstream.com"):
        """Test sending Order creation and submission email notifications.

        Args:
            test_order_id (str, optional): Order to send the notifications about.
                                           Defaults to an Id in dev: "01c3f60f-6389-4acc-b67a-591e8dac8e5d".
            test_email (str, optional): Can use it to send email where you want it.
                                        If order has a valid email, then set this to None.
                                        Defaults to ensure valid email: "mwickey@trydownstream.com".
        """

        # NOTE: Use test emails that actually work.
        # https://yopmail.com/email-generator

        order = Order.objects.get(id=test_order_id)
        if test_email:
            order.order_group.user.email = test_email
        else:
            test_email = order.order_group.user.email

        # Test order submission
        order.set_tracked_data({'submitted_on': None})
        notifications.signals.on_order_post_save(Order, instance=order)

        # Test order status change
        order.set_tracked_data({'status': Order.STATUS_CHOICES[3][0], 'submitted_on': order.submitted_on})
        notifications.signals.on_order_post_save(Order, instance=order)

        print(f"Check your email at {test_email} for the test notifications.")
