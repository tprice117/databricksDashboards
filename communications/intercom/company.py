import requests
from typing import Dict, Union

from communications.intercom.utils.utils import IntercomUtils
from communications.intercom.typings import CompanyType


class Company:
    @staticmethod
    def all() -> Dict[str, CompanyType]:
        """
        Get all Companies from Intercom.
        Data structure: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Companies/company/

        Returns:
            Dict[str, CompanyType]: Where str is the company ID.
        """
        page = 1
        items = {}
        while True:
            response = IntercomUtils.get_page("companies", page)

            # Page data.
            data = response["data"]
            for item in data:
                items[item["id"]] = CompanyType(item)
            # items.extend(data)
            if response["pages"]["total_pages"] == page:
                break
            page += 1
        return items

    @staticmethod
    def get(intercom_id: str) -> Union[CompanyType, None]:
        """Get a Company from Intercom by its ID.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Companies/retrieveCompany/

        Args:
            intercom_id (str): The UserGroup.intercom_id in Downstream DB.

        Returns:
            Union[CompanyType, None]: Returns ContactType if api completed successfully, else None.
        """
        resp = IntercomUtils.get("companies", intercom_id)

        if resp.status_code < 400:
            return resp.data
        elif resp.status_code == 404:
            pass  # Company not found
        else:
            # TODO: Log error or raise exception
            pass

    @staticmethod
    def update_or_create(company_id: str, name: str) -> Union[CompanyType, None]:
        """Updates or creates a Company in Intercom.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Companies/createOrUpdateCompany/

        Args:
            company_id (str): Id of the company in Downstream DB.
            name (str): Name of the company.

        Returns:
            Union[CompanyType, None]: Returns CompanyType if api completed successfully, else None.
        """
        resp = requests.post(
            "https://api.intercom.io/companies",
            headers=IntercomUtils.headers,
            json={
                "id": company_id,
                "name": name
            },
        )

        if resp.status_code < 400:
            return CompanyType(resp.json())
        else:
            # TODO: Log error or raise exception.
            pass

    @staticmethod
    def delete(intercom_id: str) -> Union[dict, None]:
        """Delete a Company from Intercom by its ID.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Companies/deleteCompany/

        Args:
            intercom_id (str): The UserGroup.intercom_id in Downstream DB.

        Returns:
            Union[dict, None]: Returns dictionary containing id and bool deleted if successful, else None.
        """
        resp = IntercomUtils.delete("companies", intercom_id)

        if resp.status_code < 400:
            return resp.data
        elif resp.status_code == 404:
            pass  # Company not found
        else:
            # TODO: Log error or raise exception
            pass
