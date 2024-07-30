import datetime


def get_last_day_of_previous_month():
    # Get the current date
    current_date = datetime.datetime.now()

    # Calculate the first day of the current month
    first_day_of_current_month = datetime.datetime(
        current_date.year, current_date.month, 1
    )

    # Calculate the last day of the previous month
    last_day_of_previous_month: datetime.datetime
    last_day_of_previous_month = first_day_of_current_month - datetime.timedelta(days=1)

    return last_day_of_previous_month
