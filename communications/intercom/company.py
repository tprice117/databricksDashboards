import requests
from django.conf import settings

from communications.intercom.utils.utils import IntercomUtils


class Company:
    @staticmethod
    def all():
        """
        Get all Companies from Intercom.
        """
        return IntercomUtils.get_all("companies")

    @staticmethod
    def get(company_id: str):
        """
        Get a Company from Intercom by its ID.
        """
        return IntercomUtils.get("companies", company_id)

    @staticmethod
    def create(company_id: str, name: str):
        """
        Create a Company in Intercom.
        """
        return IntercomUtils.create(
            "companies",
            {
                "company_id": company_id,
                "name": name,
            },
        )

    @staticmethod
    def update(company_id: str, name: str):
        """
        Update a Company in Intercom.
        """
        return IntercomUtils.update(
            "companies",
            company_id,
            {
                "name": name,
            },
        )

    @staticmethod
    def delete(company_id: str):
        """
        Delete a Company from Intercom by its ID.
        """
        return IntercomUtils.delete("companies", company_id)
