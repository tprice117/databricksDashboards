import requests
from django.conf import settings


class IntercomUtils:
    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_ACCESS_TOKEN}",
    }

    @staticmethod
    def create(
        endpoint: str,
        data: dict,
    ):
        """
        Create an item in an Intercom endpoint.
        """
        return requests.post(
            f"https://api.intercom.io/{endpoint}",
            headers=IntercomUtils.headers,
            json=data,
        ).json()

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
    ):
        """
        Get an item from an Intercom endpoint by its ID.
        """
        return requests.get(
            f"https://api.intercom.io/{endpoint}/{item_id}",
            headers=IntercomUtils.headers,
        ).json()

    @staticmethod
    def update(
        endpoint: str,
        item_id: str,
        data: dict,
    ):
        """
        Update an item from an Intercom endpoint.
        """
        return requests.put(
            f"https://api.intercom.io/{endpoint}/{item_id}",
            headers=IntercomUtils.headers,
            json=data,
        ).json()

    @staticmethod
    def delete(
        endpoint: str,
        item_id: str,
    ):
        """
        Delete an item from an Intercom endpoint.
        """
        return requests.delete(
            f"https://api.intercom.io/{endpoint}/{item_id}",
            headers=IntercomUtils.headers,
        ).json()
