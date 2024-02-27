import requests
from django.conf import settings

from communications.intercom.utils.utils import IntercomUtils


class Contact:
    @staticmethod
    def all():
        """
        Get all Contacts from Intercom.
        """
        return IntercomUtils.get_all("contacts")

    @staticmethod
    def get(company_id: str):
        """
        Get a Contact from Intercom by its ID.
        """
        return IntercomUtils.get("contacts", company_id)

    @staticmethod
    def create(company_id: str, name: str):
        """
        Create a Contact in Intercom.
        """
        return IntercomUtils.create(
            "contacts",
            {
                "company_id": company_id,
                "name": name,
            },
        )

    @staticmethod
    def update(company_id: str, name: str):
        """
        Update a Contact in Intercom.
        """
        return IntercomUtils.update(
            "contacts",
            company_id,
            {
                "name": name,
            },
        )

    @staticmethod
    def delete(company_id: str):
        """
        Delete a Contact from Intercom by its ID.
        """
        return IntercomUtils.delete("contacts", company_id)

    @staticmethod
    def attach_user(
        company_id: str,
        contact_id: str,
    ):
        """
        Attach a User to a Contact in Intercom.
        """
        return requests.post(
            f"https://api.intercom.io/contacts/{contact_id}/companies",
            headers=IntercomUtils.headers,
            json={
                "id": company_id,
            },
        ).json()

    @staticmethod
    def search_by_user_id(user_id: str):
        """
        Search for a Contact in Intercom by its User ID.
        """
        return requests.post(
            f"https://api.intercom.io/contacts/search",
            headers=IntercomUtils.headers,
            body={
                "query": {
                    "field": "custom_attributes.user_id",
                    "operator": "=",
                    "value": user_id,
                },
            },
        ).json()["data"]
