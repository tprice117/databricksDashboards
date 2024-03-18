import requests
from typing import Optional, Union
import re
import logging

from communications.intercom.utils.utils import IntercomUtils
from communications.intercom.typings import CompanyType, ContactType


logger = logging.getLogger(__name__)


def extract_id_from_error(err: str) -> Optional[str]:
    # Regular expression to extract the part after "id="
    # /S matched all non-whitespace characters.
    match = re.search(r"id=(\S+)", err)

    if match:
        # Group 1 captures the id string
        return match.group(1)
    else:
        return None


class Contact:
    @staticmethod
    def all():
        """
        Get all Contacts from Intercom.
        """
        return IntercomUtils.get_all("contacts")

    @staticmethod
    def get(contact_id: str) -> Union[ContactType, None]:
        """Get a Contact from Intercom by its ID.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Contacts/ShowContact/

        Args:
            contact_id (str): User.intercom_id in Downstream DB.

        Returns:
            Union[ContactType, None]: Returns ContactType if api completed successfully, else None.
        """
        resp = IntercomUtils.get("contacts", contact_id)
        if resp.status_code < 400:
            return ContactType(resp.data)
        elif resp.status_code == 404:
            logger.error(f"Contact.get: [{resp.status_code}]-[NOT FOUND]")
        elif resp.status_code == 409:
            err_list = resp.data.get("errors", [])
            for err in err_list:
                if err["code"] == "conflict":
                    contact_id = extract_id_from_error(err["message"])
                    if contact_id:
                        return Contact.get(contact_id)
            logger.error(f"Contact.get: [{resp.status_code}]-[{resp.data}]")
        else:
            logger.error(f"Contact.get: [{resp.status_code}]-[{resp.data}]")

    @staticmethod
    def create(
        external_id: str, email: str, name: str = None, phone: str = None, avatar: str = None,
        custom_attributes: dict = None
    ) -> Union[ContactType, None]:
        """Create a Contact in Intercom. If contact already exists, it returns that contact.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Contacts/CreateContact/

        Args:
            external_id (str): The User.id UUIDField.
            email (str): The User.email
            name (str, optional): The name of the User, preferrably first_name + last_name. Defaults to None.
            phone (str, optional): The User.phone. Defaults to None.
            avatar (str, optional): The User.photo_url. Defaults to None.
            custom_attributes (dict, optional): Pass in custom attributes in a dictionary to be added to Intercom
                                                Contact. Defaults to None.

        Returns:
            Union[ContactType, None]: Returns ContactType if api completed successfully, else None.
        """
        api_data = {
            "external_id": external_id,
            "email": email
        }
        if name:
            api_data["name"] = name
        if phone:
            api_data["phone"] = phone
        if avatar:
            api_data["avatar"] = avatar
        if custom_attributes:
            api_data["custom_attributes"] = custom_attributes
        resp = IntercomUtils.create("contacts", api_data)

        if resp.status_code < 400:
            return ContactType(resp.data)
        elif resp.status_code == 409:
            err_list = resp.data.get("errors", [])
            for err in err_list:
                if err["code"] == "conflict":
                    contact_id = extract_id_from_error(err["message"])
                    if contact_id:
                        if err["message"].find("archived") != -1:
                            # Unarchive contact
                            return Contact.unarchive(contact_id)
                        else:
                            return Contact.get(contact_id)
            logger.error(f"Contact.create: [{resp.status_code}]-[{resp.data}]")
        else:
            logger.error(f"Contact.create: [{resp.status_code}]-[{resp.data}]")

    @staticmethod
    def update(contact_id: str, external_id: str, email: str, name: str = None, phone: str = None, avatar: str = None,
               custom_attributes: dict = None) -> Union[ContactType, None]:
        """Update a Contact in Intercom.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Contacts/UpdateContact/

        Args:
            contact_id (str): User.intercom_id in Downstream DB.
            external_id (str): User.id UUIDField.
            email (str): User.email
            name (str, optional): User.full_name. Defaults to None.
            phone (str, optional): User.phone. Defaults to None.
            avatar (str, optional): User.photo_url. Defaults to None.
            custom_attributes (dict, optional): Pass in custom attributes in a dictionary. Defaults to None.

        Returns:
            Union[ContactType, None]: Returns ContactType if api completed successfully, else None.
        """
        api_data = {
            "external_id": external_id,
            "email": email
        }
        if name:
            api_data["name"] = name
        if phone:
            api_data["phone"] = phone
        if avatar:
            api_data["avatar"] = avatar
        if custom_attributes:
            api_data["custom_attributes"] = custom_attributes
        resp = IntercomUtils.update("contacts", contact_id, api_data)

        if resp.status_code < 400:
            return ContactType(resp.data)
        elif resp.status_code == 404:
            logger.error(f"Contact.update: [{resp.status_code}]-[NOT FOUND]")  # User not found
        else:
            logger.error(f"Contact.update: [{resp.status_code}]-[{resp.data}]")

    @staticmethod
    def delete(contact_id: str) -> Union[dict, None]:
        """Delete a Contact from Intercom by its ID.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Contacts/DeleteContact/

        Args:
            contact_id (str): The User.intercom_id in Downstream DB.

        Returns:
            Union[dict, None]: Returns dictionary with id, external_id, and deleted bool if successful, else None.
        """
        resp = IntercomUtils.delete("contacts", contact_id)

        if resp.status_code < 400:
            return resp.data
        elif resp.status_code == 404:
            logger.warning(f"Contact.delete: [{resp.status_code}]-[NOT FOUND]")  # Contact not found
        else:
            logger.error(f"Contact.update: [{resp.status_code}]-[{resp.data}]")
            pass

    @staticmethod
    def attach_user(
        company_id: str,
        contact_id: str,
    ) -> Union[CompanyType, None]:
        """Attach a User to a Contact in Intercom.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Contacts/attachContactToACompany/

        Args:
            company_id (str): UserGroup.intercom_id
            contact_id (str): User.intercom_id

        Returns:
            Union[CompanyType, None]: Returns CompanyType if found, else None.
        """
        resp = requests.post(
            f"https://api.intercom.io/contacts/{contact_id}/companies",
            headers=IntercomUtils.headers,
            json={
                "id": company_id,
            },
        )

        if resp.status_code < 400:
            return CompanyType(resp.json())
        elif resp.status_code == 404:
            logger.error(f"Contact.attach_user: [{resp.status_code}]-[{resp.content}]")  # Company not found
        else:
            logger.error(f"Contact.attach_user: [{resp.status_code}]-[{resp.content}]")

    @staticmethod
    def search_by_user_id(user_id: str):
        """
        Search for a Contact in Intercom by its User ID.
        """
        return requests.post(
            "https://api.intercom.io/contacts/search",
            headers=IntercomUtils.headers,
            json={
                "query": {
                    "field": "custom_attributes.user_id",
                    "operator": "=",
                    "value": user_id,
                },
            },
        ).json()["data"]

    @staticmethod
    def search_by_email(email: str) -> Union[ContactType, None]:
        """Search for a Contact in Intercom by its email.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Contacts/SearchContacts/

        Args:
            email (str): Email to search for.

        Returns:
            Union[ContactType, None]: Returns ContactType if found, else None.
        """
        resp = requests.post(
            "https://api.intercom.io/contacts/search",
            headers=IntercomUtils.headers,
            json={
                "query": {
                    "field": "email",
                    "operator": "=",
                    "value": email,
                },
            },
        )
        if resp.status_code < 400:
            if resp.json()["data"]:
                return ContactType(resp.json()["data"][0])

    @staticmethod
    def unarchive(contact_id: str) -> Union[ContactType, None]:
        """Unarchive a Contact from Intercom by its ID.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Contacts/UnarchiveContact/

        Args:
            contact_id (str): User.intercom_id in Downstream DB.

        Returns:
            Union[ContactType, None]: Returns ContactType if api completed successfully, else None.
        """
        resp = requests.post(
            f"https://api.intercom.io/contacts/{contact_id}/unarchive",
            headers=IntercomUtils.headers
        )
        if resp.status_code < 400:
            return Contact.get(contact_id)
        else:
            logger.error(f"Contact.unarchive: [{resp.status_code}]-[{resp.content}]")
