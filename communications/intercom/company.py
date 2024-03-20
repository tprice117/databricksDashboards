import requests
from typing import Dict, Union
import logging

from communications.intercom.utils.utils import IntercomUtils
from communications.intercom.typings import CompanyType, CustomAttributesType

logger = logging.getLogger(__name__)


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
            logger.error(f"Company.get: [{resp.status_code}]-[NOT FOUND]")  # Company not found
        else:
            logger.error(f"Company.get: [{resp.status_code}]-[{resp.data}]")

    @staticmethod
    def update_or_create(
        company_id: str, name: str, custom_attributes: CustomAttributesType = None
    ) -> Union[CompanyType, None]:
        """Updates or creates a Company in Intercom.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Companies/createOrUpdateCompany/

        Args:
            company_id (str): Id of the company in Downstream DB.
            name (str): Name of the company.
            custom_attributes (CustomAttributesType, optional): Intercom company custom_attributes. Defaults to None.
                                                                Note: New attributes need to be created in Intercom
                                                                before use.

        Returns:
            Union[CompanyType, None]: Returns CompanyType if api completed successfully, else None.
        """
        api_params = {
            "id": company_id,
            "name": name
        }
        if custom_attributes is not None:
            api_params['custom_attributes'] = custom_attributes
        resp = requests.post(
            "https://api.intercom.io/companies",
            headers=IntercomUtils.headers,
            json=api_params,
        )
        if resp.status_code < 400:
            return CompanyType(resp.json())
        else:
            logger.error(
                f"Company.update_or_create: company_id:[{company_id}], name:[{name}], response:{resp.status_code}-[{resp.content}]")

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
            logger.warning(f"Company.delete: [{resp.status_code}]-[NOT FOUND]")   # Company not found
        else:
            logger.error(f"Company.delete: [{resp.status_code}]-[{resp.data}]")
