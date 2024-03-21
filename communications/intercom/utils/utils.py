import requests
import decimal
import uuid
from django.utils.timezone import is_aware
from django.utils.duration import duration_iso_string
import datetime
from dataclasses import dataclass
from django.conf import settings


def get_json_safe_value(val):
    """Returns a JSON serializable value.
    Handles datetimes, decimals, and UUIDs (code is mostly from DjangoJSONEncoder).

    Raises:
        ValueError: Raises an error if a timezone aware time is passed in.
    """
    if isinstance(val, datetime.datetime):
        r = val.isoformat()
        if val.microsecond:
            r = r[:23] + r[26:]
        if r.endswith('+00:00'):
            r = r[:-6] + 'Z'
        return r
    elif isinstance(val, datetime.date):
        return val.isoformat()
    elif isinstance(val, datetime.time):
        if is_aware(val):
            raise ValueError("JSON can't represent timezone-aware times.")
        r = val.isoformat()
        if val.microsecond:
            r = r[:12]
        return r
    elif isinstance(val, datetime.timedelta):
        return duration_iso_string(val)
    elif isinstance(val, (decimal.Decimal, uuid.UUID)):
        return str(val)
    else:
        return val


@dataclass
class IntercomResponse():
    data: any
    # https://developers.intercom.com/docs/references/rest-api/errors/http-responses/
    status_code: int


class IntercomUtils:
    """Refer to REST api docs: https://developers.intercom.com/docs/references/introduction/
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.INTERCOM_ACCESS_TOKEN}",
    }

    @staticmethod
    def create(
        endpoint: str,
        data: dict,
    ) -> IntercomResponse:
        """Create an item in an Intercom endpoint.

        Args:
            endpoint (str): Endpoint to update (contacts, companies, etc.).
            data (dict): Dict of data to create the item.

        Returns:
            IntercomResponse: Response will contain status_code and data, which is the api json.
        """
        response = requests.post(
            f"https://api.intercom.io/{endpoint}",
            headers=IntercomUtils.headers,
            json=data,
        )
        return IntercomResponse(data=response.json(), status_code=response.status_code)

    @staticmethod
    def get_all(
        endpoint: str,
    ):
        """
        Get all items from an Intercom endpoint.
        """
        page = 1
        items = []
        while True:
            response = IntercomUtils.get_page(endpoint, page)

            # Page data.
            data = response["data"]

            items.extend(data)
            if response["pages"]["total_pages"] == page:
                break
            page += 1
        return items

    @staticmethod
    def get_page(
        endpoint: str,
        page: int,
    ):
        """
        Get a page of items from an Intercom endpoint.
        """
        return requests.get(
            f"https://api.intercom.io/{endpoint}?per_page=25&page={page}",
            headers=IntercomUtils.headers,
        ).json()

    @staticmethod
    def get(
        endpoint: str,
        item_id: str,
    ) -> IntercomResponse:
        """
        Get an item from an Intercom endpoint by its ID.
        """
        response = requests.get(
            f"https://api.intercom.io/{endpoint}/{item_id}",
            headers=IntercomUtils.headers,
        )
        return IntercomResponse(data=response.json(), status_code=response.status_code)

    @staticmethod
    def update(
        endpoint: str,
        item_id: str,
        data: dict,
    ) -> IntercomResponse:
        """Update an item from an Intercom endpoint.

        Args:
            endpoint (str): Endpoint to update (contacts, companies, etc.).
            item_id (str): Id of the item to update (contact_id, company_id, etc.).
            data (dict): Dict of data to update.

        Returns:
            IntercomResponse: Response will contain status_code and data, which is the api json.
        """
        response = requests.put(
            f"https://api.intercom.io/{endpoint}/{item_id}",
            headers=IntercomUtils.headers,
            json=data,
        )
        return IntercomResponse(data=response.json(), status_code=response.status_code)

    @staticmethod
    def delete(
        endpoint: str,
        item_id: str,
    ) -> IntercomResponse:
        """
        Delete an item from an Intercom endpoint.
        """
        response = requests.delete(
            f"https://api.intercom.io/{endpoint}/{item_id}",
            headers=IntercomUtils.headers,
        )
        return IntercomResponse(data=response.json(), status_code=response.status_code)
