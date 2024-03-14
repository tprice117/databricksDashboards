import requests
from dataclasses import dataclass
from django.conf import settings

# Intercom API typings


@dataclass
class IntercomResponse():
    data: any
    # https://developers.intercom.com/docs/references/rest-api/errors/http-responses/
    status_code: int


class IntercomUtils:
    """Refer to REST api docs: https://developers.intercom.com/docs/references/introduction/
    """
    headers = {
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
