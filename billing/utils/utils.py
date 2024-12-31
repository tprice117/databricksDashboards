import datetime

from api.models import OrderLineItem, UserAddress, UserGroup


class Utils:
    def is_user_address_project_complete_and_needs_invoice(
        user_address: UserAddress,
    ):
        """
        Check if all OrderGroups for the UserAddress are complete (end date is on or
        before the "buffer" window (currently same day)) and has line items that need
        to be invoiced.
        """
        completed_order_groups = user_address.order_groups.filter(
            end_date__lte=datetime.date.today(),
        )
        line_items_needing_invoicing = OrderLineItem.objects.filter(
            order__order_group__in=completed_order_groups,
            stripe_invoice_line_item_id__isnull=True,
        )

        # If all OrderGroups are complete and there are line items needing invoicing,
        # return True.
        return (
            completed_order_groups.count() == user_address.order_groups.count()
            and line_items_needing_invoicing.exists()
        )

    def is_user_groups_invoice_date(user_group: UserGroup):
        """
        Check if today is the invoice day for the UserGroup.
        """
        # First check if the user group has an immediate invoice frequency.
        if (
            user_group.invoice_frequency
            and user_group.invoice_frequency == UserGroup.InvoiceFrequency.IMMEDIATELY
        ):
            return True
        elif (
            user_group.invoice_frequency
            and user_group.invoice_frequency == UserGroup.InvoiceFrequency.MONTHLY
        ):
            # MONTHLY.
            # If the user group has a monthly billing cycle, check if today is the 5th.
            return Utils._is_monthly_monthly_invoice_day()
        elif (
            user_group.invoice_frequency
            and user_group.invoice_frequency == UserGroup.InvoiceFrequency.BI_WEEKLY
        ):
            return Utils._is_biweekly_invoice_day()
        elif (
            user_group.invoice_frequency
            and user_group.invoice_frequency == UserGroup.InvoiceFrequency.WEEKLY
        ):
            return Utils._is_weekly_invoice_day()
        elif user_group.invoice_day_of_month:
            # DAY OF MONTH.
            # If the user group has a specific invoice day of the month, use that.
            return datetime.date.today().day == user_group.invoice_day_of_month
        elif user_group.invoice_at_project_completion:
            return False  # Invoicing is handled by the project completion process.
        else:
            return True

    def _is_monthly_monthly_invoice_day():
        """
        Check if today is the monthly invoice day for the UserGroup.
        Currently, the monthly invoice day is the 5th of the month.
        """
        return datetime.date.today().day == 5

    def _is_biweekly_invoice_day():
        """
        Check if today is the bi-weekly invoice day for the UserGroup.

        This method assumes bi-weekly invoice days are alternating Wednesdays starting
        on a specific date (not necessarily Jan 1, 2024). It calculates the first
        bi-weekly Wednesday based on the specified start date and checks if today
        matches the pattern.

        Args:
            None (implicit self for class methods)

        Returns:
            bool: True if today is a bi-weekly invoice day, False otherwise.
        """

        # Replace these with your specific values
        inital_wednesday = Utils._get_first_wednesday_of_year(2024)
        invoice_interval = 14  # 14 days between invoices.

        # Is today a Wednesday and is divisible by 14 days from the initial Wednesday
        # (means today is a bi-weekly invoice day)?
        is_wednesday = datetime.date.today().weekday() == 2
        days_between = (
            datetime.date.today() - inital_wednesday
        ) % invoice_interval == 0
        return is_wednesday and days_between

    def _is_weekly_invoice_day():
        """
        Check if today is the weekly invoice day for the UserGroup.
        """
        # return if today is Wednesday.
        return datetime.date.today().weekday() == 2

    def _get_first_wednesday_of_year(year):
        """
        This function returns the date of the first Wednesdays of the given year.

        Args:
            year: The integer representing the year (e.g., 2024).

        Returns:
            The date of the first Wednesdays of the year in YYYY-MM-DD format.
        """
        # Create a date object for January 1st of the year
        date_obj = datetime.date(year, 1, 1)

        # Find the closest Wednesday based on the weekday of January 1st
        while date_obj.weekday() != 2:
            date_obj += datetime.timedelta(days=1)

        return date_obj
