from django.utils import timezone
from django.db.models import Q, Sum, Prefetch

from api.models import Payout, SellerLocation, User
from common.models.choices.user_type import UserType
from common.utils import customerio

TEMPLATE_ID = 13


def calculate_last_saturday():
    """Calculate the date of the last Saturday."""
    today = timezone.now().date()
    last_saturday = today - timezone.timedelta(days=(today.weekday() + 2) % 7)
    return last_saturday


def get_grouped_payouts(start_date, end_date):
    """Get total payouts for each SellerLocation within a date range."""
    return (
        Payout.objects.select_related(
            "order__order_group__seller_product_seller_location__seller_location",
            "order__order_group__seller_product_seller_location__seller_location__seller__usergroup",
        )
        .filter(Q(created_on__date__gte=start_date) & Q(created_on__date__lte=end_date))
        .values(
            "order__order_group__seller_product_seller_location__seller_location",
        )
        .annotate(total_amount=Sum("amount"))
    )


def get_seller_location_with_billing_users(seller_location_id):
    """Fetch SellerLocation with prefetching billing users."""
    return SellerLocation.objects.prefetch_related(
        Prefetch(
            "seller__usergroup__users",
            queryset=User.objects.filter(type=UserType.BILLING),
        )
    ).get(id=seller_location_id)


def send_supplier_remittance_emails():
    """Notifying suppliers of their payouts that were submitted this week for the related payout period.
    Trigger Logic:  Every Friday when a Seller has a related payout.created_on between last Saturday and today
    """
    # Get all Payouts since last Saturday.
    last_saturday = calculate_last_saturday()
    today = timezone.now().date()
    grouped_payouts = get_grouped_payouts(last_saturday, today)

    for payout in grouped_payouts:
        seller_location = get_seller_location_with_billing_users(
            payout[
                "order__order_group__seller_product_seller_location__seller_location"
            ],
        )

        emails = seller_location.seller.usergroup.users.values_list(
            "email", flat=True
        ).distinct()
        emails.append(seller_location.order_email)

        message_data = {
            "payout_total": payout["total_amount"],  # payout_total
            "seller_location_name": seller_location.name,  # seller_location_name
            "seller_location_mailing_address": seller_location.formatted_address,  # seller_location_mailing_address
            "user_group_name": seller_location.seller.usergroup.name
            if hasattr(seller_location.seller, "usergroup")
            else seller_location.seller.name,  # user_group_name
        }

        customerio.send_email(
            emails=emails,
            message_data=message_data,
            subject=f"{message_data["user_group_name"]}'s Weekly Payout Remittance from Downstream Marketplace",
            template_id=TEMPLATE_ID,
        )
